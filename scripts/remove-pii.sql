delete
from book_lists
where type = 'PERSONAL';

delete
from class_groups;

delete
from collection_item_activity_log;

delete
from collections
where user_id is not null;

refresh materialized view work_collection_frequency;

delete
from educators;
delete
from readers;
delete
from public_readers;
delete
from parents;
delete
from school_admins;
delete
from students;
delete
from supporters;
delete
from wriveted_admins;

delete
from events;
delete
from users;
delete
from subscriptions;

delete
from supporter_reader_association;

DELETE
FROM labelset_reading_ability_association
WHERE labelset_id IN (SELECT id FROM labelsets WHERE summary_origin = 'PREDICTED_NIELSEN');

delete
from labelsets
where summary_origin = 'PREDICTED_NIELSEN';

delete FROM collections
    where id in (
        select c.id from collections c LEFT JOIN collection_items ci ON c.id = ci.collection_id
WHERE ci.id IS NULL);
