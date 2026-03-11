from celery import shared_task 
import logging
from pathlib import Path

from core.models import *
import os
from datetime import datetime
from django.core.mail import send_mail
from django.core.files import File
import sys, pymupdf, pyttsx3
import shutil
from core.validators import check_isbn, check_isbn_task
from core.utils import *
BASE_DIR = Path(__file__).resolve().parent.parent


@shared_task
def housekeep():
    try:
        error = False
        from django.conf import settings
        logger = logging.getLogger('celery')
        logger.info('Housekeep now active.!')

        # overdue reminders
        overduesweep = False
        new_overdues = []
        existing_overdues = []
        loans = Loan.objects.filter(active=True)
        for loan in loans:
            if datetime.combine(loan.end_date, datetime.min.time()) < datetime.combine(datetime.now(), datetime.min.time()) and loan.active==True and loan.custody==True:
                if loan.overdue==False:
                    loan.overdue = True
                    #ban check and alert
                    if len(Loan.objects.filter(active=True, overdue=True, user_id=loan.user_id)) > 3:
                        loan.user_id.banned = True
                        subject = f'(BLS) Notice of Ban.'
                        message = f'Dear {loan.user_id.username}. You have been banned from the BLS eLibrary, as a result of accumulating over 3 late books. To remove this ban, return the overdue books, or speak with the librarian. Kind Regards'
                        student_alert(subject, message, loan.user_id.email)

                    loan.save()
                    new_overdues.append(loan)
                else:
                    existing_overdues.append(loan)
        
        for loan in new_overdues:
            loan.save()
            logger.info(f'Loan {loan.loan_id} is now overdue.')
            subject = f'(BLS) ACTION REQUIRED - Book Loan Overdue: {loan.book.title}!'
            message = f'Dear {loan.user_id.username} \n\nThis is to inform you that the book {loan.book.title} is now overdue. Please return the book to the BLS library as soon as possible.  \n\n Kindly note that failure to comply with library instrutction may result in a penalty/sanction, and having 3 or more books overdue, will result in a ban. \n\n Thank you.'
            student_alert(subject, message, loan.user_id.email)

        for loan in existing_overdues:
            loan.save()
            logger.info(f'Loan {loan.loan_id} is now overdue.')
            amount = loan.user_id.overdue_penalty(loan=loan)
            subject = f'(BLS) ACTION REQUIRED - Book Loan Overdue: {loan.book.title}!'
            message = f'Dear {loan.user_id.username} \n\nThis is to remind you that the book {loan.book.title} is still overdue. Please return the book to the BLS library as soon as possible.  \n\n Kindly note that, as a result, you have incurred {amount} PKR in penalties and having 3 or more books overdue, will result in a ban. \n\n Thank you.'
            student_alert(subject, message, loan.user_id.email)
        overduesweep = True

        # daily re-save all books to ensure stock consistency
        books = Book.objects.all()
        booksavesweep = False
        for book in books:
            book.save()
            logger.info(f'Book {book.title} re-saved.')
        booksavesweep = True



    except:
        error = True



    # daily reporting
    if error or booksavesweep==False or overduesweep==False:
        subject = f'(BLS eLibrary) ERROR: Housekeeping Routine Failed!'
        message = f'Dear Admin, \n\nThis is to inform you that the housekeeping routine failed to run successfully. Kindly note the following flags: \n\n BookSaveSweep: {booksavesweep} \n\n OverdueSweep {overduesweep} \n\nPlease check the logs for more information. \n\n Thank you.'
        admin_alert(subject, message)
    else:
        subject = f'(BLS eLibrary) Housekeeping Report!'
        message = f'Dear Admin, \n\nThis is to inform you that the following ran housekeeping routine ran successfully. Kindly note the following flags: \n\n BookSaveSweep: {booksavesweep} \n\n OverdueSweep {overduesweep}. \n\n Thank you.'
        admin_alert(subject, message)

        subject = f'(BLS eLibrary) Daily Report!'
        message = f'Dear Librarian \n\nThis is to inform you that the housekeeping routine ran successfully. \n\n Number of new overdue books: {len(new_overdues)} \n\n Number of reminder emails sent: {len(existing_overdues)} \n\n Thank you.'
        librarian_alert(subject, message)


@shared_task
def save_books():
    logger = logging.getLogger('celery')
    try:
        books = Book.objects.all()
        for book in books:
            book.save()
            logger.info(f'Book {book.title} re-saved.')
    except Exception as exception:
        admin_alert('Book Save Error', f'Dear Admin, kindly see to the following error: {exception}')



@shared_task
def autobook():
    AUTOBOOK_PICKUP_PATH = os.path.join(settings.MEDIA_ROOT, 'autobook')
    print(AUTOBOOK_PICKUP_PATH)
    books_uploaded = []
    notdoable = []
    try:
        error = False
        logger = logging.getLogger('celery')
        logger.info('Autobook now active.!')
        files = os.listdir(AUTOBOOK_PICKUP_PATH)
        print(files)
        if len(files)>0:
            print(f'Files found: {len(files)}')
            for file in files:
                originalname = str(file)
                print(f'Processing file: {file}')
                metadata = originalname.split('_')
                if len(metadata) < 5:
                    notdoable.append(originalname)
                    continue

                title, author, isbn = metadata[0].replace('-', ' '), metadata[1].replace('-', ' '), metadata[2]
                category = metadata[3]
                physical_flag = metadata[4]

                if not check_isbn_task(isbn):
                    notdoable.append(title)
                    continue

                physical = True if physical_flag.upper() == 'T' else False

                file_path = os.path.join(AUTOBOOK_PICKUP_PATH, originalname)
                with open(file_path, 'rb') as upload_file:
                    djangofile = File(upload_file)
                    tempbook = Book(title=title, author=author, isbn=isbn, category=category, physical=physical, file=djangofile)
                    tempbook.save()
                    print(f'Book created {metadata}')

                print(f'File {originalname} removed.')
                os.remove(file_path)
                books_uploaded.append(originalname)
                
    except Exception as exception:
        print(exception)
        error = True
        subject = f'(BLS eLibrary) ERROR: AutoBook Routine Failed!'
        message = f'Dear Admin, \n\nThis is to inform you that the AutoBook routine failed to run successfully. Kindly note the following flags: \n\n Exception: {exception} \n\n Thank you.'
        admin_alert(subject, message)
    else:
        if len(notdoable) > 0:
            subject = f'(BLS eLibrary) UPLOAD: Autobook uplink, {len(notdoable)} books rejected'
            message = f'Dear Admin, \n\nThis is to inform you that the eLibrary AutoBook system ran successfully. Kindly note the following books have been uploaded: \n\n {books_uploaded} \n\n And also note the following books were rejected for incorrect formats: \n\n {notdoable} \n\n Please check the logs for more information. \n\n Thank you.'
            librarian_alert(subject, message)
        else:
            subject = f'(BLS eLibrary) UPLOAD: AutoBOOKs Uploaded!'
            message = f'Dear Admin, \n\nThis is to inform you that the eLibrary AutoBook system ran successfully. Kindly note the following books have been uploaded: \n\n {books_uploaded} \n\nPlease check the logs for more information. \n\n Thank you.'
            librarian_alert(subject, message)



@shared_task
def storage_optimiser():
    try:
        for book in Book.objects.all():
            dir_cov = os.path.join(settings.MEDIA_ROOT, 'covers')
            dir_book = os.path.join(settings.MEDIA_ROOT, 'books')
            filename = f'{book.title}_{book.author}.jpg'

            if filename in os.listdir(dir_cov):
                os.remove(os.path.join(dir_cov, filename))
            
            if filename in os.listdir(dir_book):
                os.remove(os.path.join(dir_book, filename))
        
        tempclean = False
        temp_path = os.path.join(BASE_DIR, 'core', 'temps')
        temp_files = os.listdir(temp_path)
        for servedpdf in temp_files:
            if os.path.isfile(os.path.join(temp_path, servedpdf)):
                os.remove(os.path.join(temp_path, servedpdf))
        
        tempclean = True
        
        servedclean = False
        served_path = os.path.join(BASE_DIR, 'media', 'servedpdfs')
        served_files = os.listdir(served_path)
        for servedpdf in served_files:
            if os.path.isfile(os.path.join(served_path, servedpdf)):
                os.remove(os.path.join(served_path, servedpdf))
        
        servedclean = True

        subject = f'(BLS) eLibrary - StorageSweep Complete'
        message = f'Dear Admin,\n Kindly note, the storage optimising function has run, with the following metrics\n TempClean: {tempclean}.\n ServedClean: {servedclean} Kind Regards'
        admin_alert(subject, message)
    except Exception as error:
        subject = f'(BLS) eLibrary - StorageSweep Failure'
        message = f'Dear Admin \n Kindly note the Storage Sweep function failed with the following exception: {error}\n and the following metrics: TempClean: {tempclean}\n ServedClean: {servedclean}\n. Kindly fix.'
        admin_alert(subject, message)
    

#placed here to avoid long processing time while uploading
@shared_task
def text_extract():
    books = Book.objects.all()
    emptybooks = list(filter(lambda book: len(book.text) == 0, books))
    for book in emptybooks:
        book.text_extract()

@shared_task
def audiobook_maker():
    books = Book.objects.all()
    books = list(filter(lambda book: len(book.text) > 0, books))
    noaudio = list(filter(lambda book: book.audio_version == False, books))
    for book in noaudio:
        book.audio_maker()

@shared_task
def monthly_roundup():
    no_stock_notes = LoanIssuanceNotes.objects.filter(flag=1, issued=False)
    no_stock = list(filter(lambda note: note.creation_date > datetime.now() - timedelta(days=30), no_stock_notes))
    # flag1 indicates lack of stock, and issued false indicates that the book was not issued
    frequencies = {}
    for note in no_stock:
        if note.book.title in frequencies:
            frequencies[note.book.title] += 1
        else:
            frequencies[note.book.title] = 1
    #
    print(frequencies)
    booksinorder = sorted(frequencies, key=frequencies.get, reverse=True)
    subject = f'(BLS) Monthly Roundup'
    message = f'Dear Admin, \n\n As this month comes to a close, kindly find below the top 3 books that were requested for loan, but rejected due to insufficient stock. This is intended to guide you as to which books to order more stock of \n\n {booksinorder} \n\n DIAGNOSTIC: {frequencies} \n\n'

    librarian_alert(subject, message)
            

    




