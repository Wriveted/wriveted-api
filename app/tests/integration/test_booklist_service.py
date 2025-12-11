import pytest
from sqlalchemy import and_, select
from sqlalchemy.orm import joinedload

from app import crud
from app.models.booklist import BookList
from app.models.booklist_work_association import BookListItem
from app.models.labelset import LabelSet, RecommendStatus
from app.models.labelset_hue_association import LabelSetHue, Ordinal
from app.models.labelset_reading_ability_association import LabelSetReadingAbility
from app.models.work import Work
from app.repositories.labelset_repository import labelset_repository
from app.services.booklists import generate_reading_pathway_lists
from app.services.recommendations import gen_next_reading_ability


@pytest.mark.asyncio
async def test_read_now_read_next_generation(
    session, test_user_account, test_huey_attributes, works_list
):
    assert not any(
        bl.name in ["Books To Read Now", "Books To Read Next"]
        for bl in test_user_account.booklists
    )

    # to be removed afterwards
    scoped_orm_items = []

    # add 10 recommendable books that don't match the test huey attributes
    bad_works = works_list[0:10]
    for work in bad_works:
        session.add(work)
        labelset = labelset_repository.create(
            session,
            obj_in={
                "min_age": 90,
                "max_age": 100,
                "huey_summary": "A good book but maybe not for you",
                "recommend_status": RecommendStatus.GOOD,
            },
        )
        scoped_orm_items.append(labelset)
        session.flush()
        work.labelset = labelset
        session.add(
            LabelSetHue(labelset_id=labelset.id, hue_id=9, ordinal=Ordinal.PRIMARY)
        )
        session.add(
            LabelSetReadingAbility(labelset_id=labelset.id, reading_ability_id=5)
        )

    # add 10 recommendable books that match the current reading ability and hues
    good_for_now_works = works_list[10:20]
    for work in good_for_now_works:
        session.add(work)
        labelset = labelset_repository.create(
            session,
            obj_in={
                "min_age": 0,
                "max_age": 10,
                "huey_summary": "A good book",
                "recommend_status": RecommendStatus.GOOD,
            },
        )
        scoped_orm_items.append(labelset)
        session.flush()
        work.labelset = labelset
        session.add(
            LabelSetHue(labelset_id=labelset.id, hue_id=1, ordinal=Ordinal.PRIMARY)
        )
        session.add(
            LabelSetReadingAbility(labelset_id=labelset.id, reading_ability_id=2)
        )

    # add 10 recommendable books that match the next reading ability and hues
    good_for_next_works = works_list[20:30]
    for work in good_for_next_works:
        session.add(work)
        labelset = labelset_repository.create(
            session,
            obj_in={
                "min_age": 0,
                "max_age": 10,
                "huey_summary": "A challenging book",
                "recommend_status": RecommendStatus.GOOD,
            },
        )
        scoped_orm_items.append(labelset)
        session.flush()
        work.labelset = labelset
        session.add(
            LabelSetHue(
                labelset_id=labelset.id,
                hue_id=3,
                ordinal=Ordinal.PRIMARY,
            )
        )
        session.add(
            LabelSetReadingAbility(labelset_id=labelset.id, reading_ability_id=3)
        )

    session.commit()

    # create the lists against the test user - this will use its own async session
    read_now_orm, read_next_orm = await generate_reading_pathway_lists(
        test_user_account.id, test_huey_attributes
    )

    # Query fresh instances from sync session to avoid session conflicts
    read_now: BookList = session.execute(
        select(BookList).where(
            and_(
                BookList.name == "Books To Read Now",
                BookList.user_id == test_user_account.id,
            )
        )
    ).scalar_one()

    read_next: BookList = session.execute(
        select(BookList).where(
            and_(
                BookList.name == "Books To Read Next",
                BookList.user_id == test_user_account.id,
            )
        )
    ).scalar_one()

    # Query the items separately to avoid lazy loading issues
    read_now_items = (
        session.execute(
            select(BookListItem)
            .options(
                joinedload(BookListItem.work)
                .joinedload(Work.labelset)
                .joinedload(LabelSet.reading_abilities),
                joinedload(BookListItem.work)
                .joinedload(Work.labelset)
                .joinedload(LabelSet.hues),
            )
            .where(BookListItem.booklist_id == read_now.id)
            .order_by(BookListItem.order_id)
        )
        .unique()
        .scalars()
        .all()
    )

    # ensure the books in 'read now' match the current reading ability (and hues)
    current_reading_ability = test_huey_attributes.reading_ability[0]
    assert read_now_items
    for item in read_now_items:
        work = item.work
        labelset = work.labelset
        expected_matching_reading_abilities = [
            ra.key for ra in labelset.reading_abilities
        ]
        assert current_reading_ability in expected_matching_reading_abilities
        assert any(
            [
                True
                for hue in [hue.key for hue in labelset.hues]
                if hue in test_huey_attributes.hues
            ]
        )

    # ensure the books in 'read next' match the next reading ability (and hues)
    next_reading_ability = gen_next_reading_ability(
        test_huey_attributes.reading_ability[0]
    )
    read_next_items = (
        session.execute(
            select(BookListItem)
            .options(
                joinedload(BookListItem.work)
                .joinedload(Work.labelset)
                .joinedload(LabelSet.reading_abilities),
                joinedload(BookListItem.work)
                .joinedload(Work.labelset)
                .joinedload(LabelSet.hues),
            )
            .where(BookListItem.booklist_id == read_next.id)
            .order_by(BookListItem.order_id)
        )
        .unique()
        .scalars()
        .all()
    )
    assert read_next_items
    for item in read_next_items:
        work = item.work
        labelset = work.labelset
        expected_matching_reading_abilities = [
            ra.key for ra in labelset.reading_abilities
        ]
        assert next_reading_ability in expected_matching_reading_abilities
        assert any(
            [
                True
                for hue in [hue.key for hue in labelset.hues]
                if hue in test_huey_attributes.hues
            ]
        )

    # ensure none of the inappropriate books made it into either list
    all_recommended = [item.work for item in read_now_items] + [
        item.work for item in read_next_items
    ]
    assert not any([True for work in all_recommended if work in bad_works])

    for item in scoped_orm_items:
        session.delete(item)
    session.commit()
