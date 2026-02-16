crucial installs include redis
poppler path ident
Extract to C:\redis
Alter redis.windows.conf line '''dir ./''' to '''dir C:/Redis/data''' and give full permissions to write and read there.
Run redis-server as admin

Commands to start CelerySystem:
redis-server --- run as an admin
celery -A core worker --loglevel=info --pool=solo
celery -A core beat --loglevel=debug --scheduler django_celery_beat.schedulers:DatabaseScheduler

AUTOMATIC BOOK PICKUP AND UPLOAD

1) UPLOAD TO '/autobooks' in folder
2) Celery will wake up and UPLOAD
MAY TRIGGER MIODEL ERROR IF ISBN NOT OF CORRECT FORMAT
3) ENSURE FORMAT AS FOLLOWS 
   '\BOOKTITLE_AUTHORNAME_ISBN_STOCKLEVEL_CATEGORYNUMBER_PHYSICALTF'
   '\HANDBOOK-ONE_EHSAN-CHUGHTAI_01891282398273_39_2_T_


BookCopy Model Designation
1) Seperate out PhysicalBook Instance w/. following attributes
    - BOOK_ID
    - PHYSICAL_ID
    - Conditions
2) Set Damages and Penalties to Specific PhysicalBook
3) Stock to be maintained centrally, however LOAN to be issued to specific Physial Book

SITE WIDE SEARCH:
 choice decicison File merging: PyMuPDF is 100+ times faster than pypdf and supports merging everything (not only PDF) with a target PDF. Annotation & Form Field ...


Books have no stock by default
