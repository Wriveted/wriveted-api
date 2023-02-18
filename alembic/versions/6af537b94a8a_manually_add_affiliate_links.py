"""Manually add affiliate links

Revision ID: 6af537b94a8a
Revises: 90707bbde53a
Create Date: 2023-02-17 17:11:52.576685

"""
import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "6af537b94a8a"
down_revision = "90707bbde53a"
branch_labels = None
depends_on = None


def upgrade():

    op.execute(
        """
    update editions
        set info = jsonb_set(info::jsonb,
            '{links}',
            '[{"type": "retailer", "url": "https://amzn.to/3Kd4cdu", "retailer": "Amazon AU"}]'::jsonb)
        where isbn='9781760150426';
    
    
    update editions
        set info = jsonb_set(info::jsonb,
            '{links}',
            '[{"type": "retailer", "url": "https://amzn.to/3YDMK6a", "retailer": "Amazon AU"}]'::jsonb)
        where isbn='9780141354828';
    
    
    update editions
        set info = jsonb_set(info::jsonb,
            '{links}',
            '[{"type": "retailer", "url": "https://amzn.to/3Ib9Km6", "retailer": "Amazon AU"}]'::jsonb)
        where isbn='9780143303831';
    
    
    
    update editions
        set info = jsonb_set(info::jsonb,
            '{links}',
            '[{"type": "retailer", "url": "https://amzn.to/3IwwNJw", "retailer": "Amazon AU"}]'::jsonb)
        where isbn='9780064407663';
    
    
    
    update editions
        set info = jsonb_set(info::jsonb,
            '{links}',
            '[{"type": "retailer", "url": "https://amzn.to/3IuQzoE", "retailer": "Amazon AU"}]'::jsonb)
        where isbn='9781925163131';
    
    
    update editions
        set info = jsonb_set(info::jsonb,
            '{links}',
            '[{"type": "retailer", "url": "https://amzn.to/3YDPxfS", "retailer": "Amazon AU"}]'::jsonb)
        where isbn='9780340999073';
    
    
    update editions
        set info = jsonb_set(info::jsonb,
            '{links}',
            '[{"type": "retailer", "url": "https://amzn.to/3Ee4dKk", "retailer": "Amazon AU"}]'::jsonb)
        where isbn='9780141359786';
    
    
    update editions
        set info = jsonb_set(info::jsonb,
            '{links}',
            '[{"type": "retailer", "url": "https://amzn.to/3KeT0Nr", "retailer": "Amazon AU"}]'::jsonb)
        where isbn='9781742837581';
    
    update editions
        set info = jsonb_set(info::jsonb,
            '{links}',
            '[{"type": "retailer", "url": "https://amzn.to/3KgWC1G", "retailer": "Amazon AU"}]'::jsonb)
        where isbn='9781921564925';
    
    update editions
        set info = jsonb_set(info::jsonb,
            '{links}',
            '[{"type": "retailer", "url": "https://amzn.to/3Efe2HV", "retailer": "Amazon AU"}]'::jsonb)
        where isbn='9781743628638';

    """
    )


def downgrade():
    isbns = [
        "9781760150426",
        "9780141354828",
        "9780143303831",
        "9780064407663",
        "9781925163131",
        "9780340999073",
        "9780141359786",
        "9781742837581",
        "9781921564925",
        "9781743628638",
    ]
    placeholders = ",".join(["%s"] * len(isbns))
    query = f"""
        update editions
            set info = jsonb_set(info::jsonb, '{{links}}', '[]'::jsonb)
            where isbn in ({placeholders});
    """
    op.execute(query, isbns)
