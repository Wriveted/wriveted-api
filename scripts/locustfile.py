"""
Setup: Install all project deps with `poetry install`
Set the environment variable `WRIVETED_API_TOKEN`
Run: `poetry -m locust` in terminal.
Open http://localhost:8089 and run a test setting the target to your local API: http://localhost:8000

https://docs.locust.io/en/stable/writing-a-locustfile.html
"""
import os
import random

from locust import HttpUser, between, task

from scripts.create_test_school import (
    get_or_create_random_class,
    get_or_create_test_school,
)

root_access_token = os.environ.get("WRIVETED_API_TOKEN")


class RootUser(HttpUser):

    # make the simulated users wait between this many seconds after each task
    wait_time = between(1, 5)

    def on_start(self):
        self.access_token = root_access_token
        self.school = get_or_create_test_school(self.client.base_url, root_access_token)
        self.school_wriveted_id = self.school["wriveted_identifier"]
        self.class_info = get_or_create_random_class(
            self.client.base_url, root_access_token, self.school_wriveted_id
        )
        self.class_group_id = self.class_info["id"]

    @task
    def test_token(self):
        self.client.get(
            "/v1/auth/me",
            headers={"Authorization": f"Bearer {self.access_token}"},
        )

    @task
    def get_test_school(self):
        school_info = self.client.get(
            f"/v1/school/{self.school['wriveted_identifier']}",
            headers={"Authorization": f"Bearer {self.access_token}"},
            name="/school/{id}",
        )
        assert "collection_count" in school_info.json()

    @task
    def get_test_class_group(self):
        class_group_info = self.client.get(
            f"/v1/class/{self.class_group_id}",
            headers={"Authorization": f"Bearer {self.access_token}"},
            name="/class/{id}",
        )
        class_group_info.raise_for_status()
        assert "student_count" in class_group_info.json()

    @task
    def register_student_and_login(self):
        if not hasattr(self, "username"):
            new_student_response = self.client.post(
                f"/v1/auth/register-student",
                json={
                    "first_name": "Loki",
                    "last_name_initial": "T",
                    "school_id": self.school_wriveted_id,
                    "class_joining_code": self.class_info["join_code"],
                },
            ).json()

            self.username = new_student_response["username"]

        print(
            f"Logging in as {self.username} with joincode: {self.class_info['join_code']}"
        )
        student_login_response = self.client.post(
            f"/v1/auth/class-code",
            json={
                "username": self.username,
                "class_joining_code": self.class_info["join_code"],
            },
        )

        self.student_api_token = student_login_response.json()["access_token"]

    @task
    def get_recomendation(self):
        if hasattr(self, "student_api_token"):
            # Get recommendation as student
            access_token = self.student_api_token
        else:
            # As root
            access_token = self.access_token

        self.client.post(
            f"/v1/recommend",
            headers={"Authorization": f"Bearer {access_token}"},
            params={"limit": 5},
            json={
                "hues": [
                    "hue01_dark_suspense",
                    "hue02_beautiful_whimsical",
                    "hue03_dark_beautiful",
                    "hue05_funny_comic",
                    "hue06_dark_gritty",
                ],
                "age": random.randint(5, 13),
                "reading_abilities": ["SPOT", "TREEHOUSE", "CHARLIE_CHOCOLATE"],
                "wriveted_identifier": self.school_wriveted_id,
            },
        )

    @task
    def get_users_and_details(self):
        users_list_response = self.client.get(
            "/v1/users",
            headers={"Authorization": f"Bearer {self.access_token}"},
            params={"limit": 5},
        )
        users_list_response.raise_for_status()
        user_briefs = users_list_response.json()["data"]

        for user_brief in user_briefs:
            if random.random() > 0.8:
                user_detail_response = self.client.get(
                    f"/v1/user/{user_brief['id']}",
                    headers={"Authorization": f"Bearer {self.access_token}"},
                    name="/user/{id}",
                )
                user_detail_response.json()

    @task
    def get_booklists_and_details(self):
        list_response = self.client.get(
            "/v1/lists",
            headers={"Authorization": f"Bearer {self.access_token}"},
            params={"list_type": "School", "limit": 5},
        )
        list_response.raise_for_status()
        list_briefs = list_response.json()["data"]

        for list_brief in list_briefs:
            if random.random() > 0.8:

                list_detail_response = self.client.get(
                    f"/list/{list_brief['id']}",
                    headers={"Authorization": f"Bearer {self.access_token}"},
                    name="/list/{id}",
                )
                list_detail_response.json()

    @task
    def get_version(self):
        self.client.get("/v1/version").json()