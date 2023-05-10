import base64
import datetime as dt
import logging
import sqlite3
import time

import httpx
import humanize as humanize
from pydantic import AnyHttpUrl, BaseSettings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("wriveted.spydus")


class Settings(BaseSettings):
    # wriveted_api: AnyHttpUrl = "http://localhost:8000/v1"
    # wriveted_api_token: str

    spydus_base_url = "https://blacktown.spydus.com"
    spydus_api_token: str | None

    spydus_client_id: str = "808C3188772BA5ECE76F74F304AF3DCC"
    spydus_client_secret: str

    output_db = "spydus.db"


def get_access_token(config: Settings):
    to_encode = f"{config.spydus_client_id}:{config.spydus_client_secret}"
    base64_encoded_id_secret = base64.b64encode(to_encode.encode()).decode()

    headers = {
        "Content-Type": "application/x-www-form-urlencoded",
        "Authorization": "Basic {}".format(base64_encoded_id_secret),
    }
    params = {"grant_type": "client_credentials"}

    response = httpx.post(
        f"{config.spydus_base_url}/api/token", headers=headers, data=params
    )
    response.raise_for_status()
    return response.json()["access_token"]


def get_manifestation_ids(config: Settings, startIndex=1, count=10, timeout=120):
    """

    Raw response is something like this:
        {'version': '1.0', 'entity-type': '01', 'selection-criterion': [], 'totalResults': 999068, 'itemsPerPage': 10, 'startIndex': 1,
        'entity': [
            {'id': '1', 'href': 'https://blacktown.spydus.com/api/lcf/1.2/manifestations/1?global=N'},
            {'id': '7', 'href': 'https://blacktown.spydus.com/api/lcf/1.2/manifestations/7?global=N'},
            {'id': '11', 'href': 'https://blacktown.spydus.com/api/lcf/1.2/manifestations/11?global=N'}
        ]
        }

    Timing wise, takes about a minute to retrieve 5000 ids. Note the API appears to have about a million.
    Perhaps we can filter for just books.
    """
    start_time = time.time()
    response = httpx.get(
        f"{config.spydus_base_url}/api/lcf/1.2/manifestations",
        params={"os:count": count, "os:startIndex": startIndex, "global": 1},
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {config.spydus_api_token}",
        },
        timeout=timeout,
    )
    logger.debug(f"Response status code: {response.status_code}")
    if response.status_code == 401:
        logger.info("Getting new token")
        config.spydus_api_token = get_access_token(config)
        raise ValueError("Auth expired - retry again")

    try:
        data = response.json()
    except Exception as e:
        logger.warning(response.status_code)
        logger.warning(f"JSON didn't parse.\n{response.text}")
    end_time = time.time()
    # logger.debug(f"Raw result: {data}")
    logger.info(
        f"Total manifestations: {data['totalResults']}. Received {len(data['entity'])} in {humanize.naturaldelta(dt.timedelta(seconds=end_time-start_time))}"
    )
    return [item["id"] for item in data["entity"]]


def get_manifestation_from_isbn(isbn, config: Settings, timeout=30):
    response = httpx.get(
        f"{config.spydus_base_url}/api/lcf/1.2/manifestations",
        params={
            "global": 1,
            "os:count": 10,
            "alt-manifestation-id": isbn,
            # https://bic-org-uk.github.io/bic-lcf/LCF-CodeLists.html#MNI
            "alt-manifestation-id-type": "03",
        },
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {config.spydus_api_token}",
        },
        timeout=timeout,
    )

    return response.json()


def get_manifestation_details(identifier, config: Settings, timeout=30):
    response = httpx.get(
        f"{config.spydus_base_url}/api/lcf/1.2/manifestations/{identifier}",
        params={
            "global": 1,
        },
        headers={
            "Accept": "application/json",
            "Authorization": f"Bearer {config.spydus_api_token}",
        },
        timeout=timeout,
    )

    return response.json()


def main():
    config = Settings()
    if config.spydus_api_token is None:
        logger.info("Getting new token")
        config.spydus_api_token = get_access_token(config)
    else:
        logger.info("Using provided token")

    print(config.spydus_api_token)

    # experiment1(config)
    # experiment2(config)

    # Scrape all manifestation ids
    con = sqlite3.connect(config.output_db)
    cur = con.cursor()
    cur.execute("CREATE TABLE IF NOT EXISTS manifestations(id PRIMARY KEY)")
    cur.execute("CREATE TABLE IF NOT EXISTS batch(ts, startIndex, count, status)")

    # See how many manifestations we've already recorded
    cur.execute("SELECT count(*) FROM manifestations")
    print("Number of manifestations in db: ", cur.fetchone()[0])

    # Remove any incomplete jobs
    cur.execute("DELETE FROM batch where status != 'completed'")
    con.commit()

    batch_size = 1000

    # Get the last completed batch to see where we should start from (assuming this has been running before)
    cur.execute(
        "SELECT startIndex FROM batch where status='completed' order by ts DESC limit 1"
    )
    res = cur.fetchone()
    if res is not None:
        start_index = res[0] + batch_size
    else:
        start_index = 1

    for iteration in range(1, 1_000):
        print(
            f"Iteration {iteration}. Current offset: {start_index}. Batch size {batch_size}"
        )

        try:
            # Add an entry for the current batch job
            cur.execute(
                "INSERT INTO batch VALUES (?, ?, ?, ?)",
                (dt.datetime.now(), start_index, batch_size, "queued"),
            )
            con.commit()
            current_batch_id = cur.lastrowid

            manifestations = get_manifestation_ids(
                config, count=batch_size, startIndex=start_index
            )
            logger.info(f"Received {len(manifestations)} manifestation ids")

            cur.executemany(
                "INSERT INTO manifestations VALUES (?) ON CONFLICT(id) DO NOTHING",
                [(m,) for m in manifestations],
            )

            cur.execute(
                f"UPDATE batch SET status=? where rowid={current_batch_id}",
                ("completed",),
            )
            con.commit()
            start_index += batch_size

        except Exception as e:
            print("Something went wrong", e)
            con.rollback()
            logger.warning("Having a sleep then will try to keep going")
            time.sleep(60)

        time.sleep(0.5)

    # See how many manifestations we've already recorded
    cur.execute("SELECT count(*) FROM manifestations")
    print("Number of manifestations in db: ", cur.fetchone()[0])

    print("Exporting all manifestation ids to plain csv file")
    filename = "manifestation-ids.csv"
    with open(filename, "wt") as f:
        cur.execute("SELECT * FROM manifestations")
        for row in cur.fetchall():
            f.write(f"{row[0]}\n")

    print(f"Output written to {filename}")


def experiment1(config):
    """
    Experiment 1 - Is it feasible to request all manifestations then get details on them?

    TL;DR - not really. Lots of items without isbns, and we don't find this out until we've queried
    for the details.

    """
    manifestations = get_manifestation_ids(config, count=100, startIndex=100)
    print(f"Received {len(manifestations)} manifestation ids")

    for identifier in manifestations:
        # Get details and map manifestation ID type "03" to ISBN
        detail = get_manifestation_details(identifier, config)
        for alternative_id in detail["additional-manifestation-id"]:
            if alternative_id["manifestation-id-type"] == "02":
                # An item with an ISBN!
                print("ISBN:", alternative_id["value"])
                print(detail)


def experiment2(config):
    """
    Experiment 2 - what about looking up a list of our ISBNs to get the BRN number.
    """
    isbns = """9780086461629
9780778790433
9781503221727
9780140860474
9781477404751
9781451705188
9781615340040
9780531213261
9780750016094
9788483578339
9780511240515
9783596900107
9780224009423
9782745984753
9780545224093
9788762677708
9780778746331
9781439578438
9788611164533
9780613632034
9780732269326
9780060875800
9789870428954
9780440315551
9780590539524
9781502895790
9781566194334
9781858139074
9783866473096
9781761041716
9781508613565
9783442244065
9781975911553
9781447277927
9789510328675
9781519631510
9788414005071
9781597371384
9780425052198
9781760550103
9781447277934
9781518933288
9780545349444
9781509810000
9783551762511
9780192794055
9781407170756
9780992571054
9788835341888
9781875763061
9789024529315
9788484499664
9781428757929
9788416401932
9786053751441
9789024556298
9789638428325
9781742766300
9781408849941
9781921143809
9781845388027
9788869662539
9781760761158
9781875168019
9780734304902
9781772267242
9780763688127
9780709706915
9781518365263
9786063341878
9788774432715
9788807902895
9781775429524
9789179532291
9780191560316
9789577316530
9781435636200
9782871294146
"""

    for i, isbn in enumerate(isbns.splitlines()[:50]):
        data = get_manifestation_from_isbn(isbn=isbn.strip(), config=config)
        if data["totalResults"] >= 1:
            print(i, data)


if __name__ == "__main__":
    main()
