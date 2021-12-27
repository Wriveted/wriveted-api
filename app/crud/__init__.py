from app.crud.base import CRUDBase

from app.crud.author import CRUDAuthor
from app.crud.edition import CRUDEdition
from app.crud.illustrator import CRUDIllustrator
from app.crud.school import CRUDSchool
from app.crud.work import CRUDWork
from app.models import Work, School, Author, Illustrator
from app.models.edition import Edition


author = CRUDAuthor(Author)
illustrator = CRUDIllustrator(Illustrator)
edition = CRUDEdition(Edition)
school = CRUDSchool(School)
work = CRUDWork(Work)
