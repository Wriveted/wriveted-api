from cProfile import label
import pytest
from sqlalchemy import select, and_

from app.models.booklist import BookList
from app.models.labelset import LabelSet, RecommendStatus
from app.models.labelset_hue_association import LabelSetHue, Ordinal
from app.models.labelset_reading_ability_association import LabelSetReadingAbility
from app.models.work import Work
from app.models.reading_ability import ReadingAbility
from app.models.hue import Hue
from app import crud
from app.schemas.labelset import LabelSetCreateIn
from app.services.booklists import generate_reading_pathway_lists
from app.services.recommendations import increment_reading_ability
from app.schemas.recommendations import ReadingAbilityKey


def test_read_now_read_next_generation(
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
        labelset = crud.labelset.create(
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
        labelset = crud.labelset.create(
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
        labelset = crud.labelset.create(
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

    # create the lists against the test user
    read_now_list, read_next_list = generate_reading_pathway_lists(
        test_user_account.id, test_huey_attributes
    )
    # scoped_orm_items.extend([read_now_list, read_next_list])

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

    # ensure the books in 'read now' match the current reading ability (and hues)
    current_reading_ability = test_huey_attributes.reading_ability[0]
    read_now_items = read_now.items.all()
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
    next_reading_ability = increment_reading_ability(
        test_huey_attributes.reading_ability[0]
    )
    read_next_items = read_next.items.all()
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
