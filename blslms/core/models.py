import shutil
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.timezone import now
from datetime import *
from django.contrib import messages
import PyPDF2
import pdf2image as pdfpck
import pdf2image
import os
from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import MaxValueValidator
from django.shortcuts import redirect, get_object_or_404
import pyttsx3
import requests
import re
import phonenumbers
import pymupdf
from core.utils import *
from django.core.validators import FileExtensionValidator
from django.contrib.auth.models import Group
from core.utils import admin_alert
from core.validators import *
from core.constants import *


def check_unique(value, book_id):
    books_excluding_current = Book.objects.exclude(book_id=book_id)
    if len(list(books_excluding_current)) == 0:
        return value
    else:
        if books_excluding_current.filter(isbn=value).exists():
            print('error')
            raise ValidationError('ISBN already exists.')
        print('all clear')
    return value


API_NINJA_KEY = 'zOTQtRmlaWZSpu7YJ9Hosg==Ow3XXv14FgauUgfE'


class AbstractModel(models.Model):
    class Meta:
        abstract = True

    creation_date = models.DateTimeField(auto_now_add=True)
    updated_date = models.DateTimeField(auto_now=True)


class PhysicalBook(AbstractModel):
    physical_id = models.AutoField(primary_key=True)
    book_id = models.ForeignKey('Book', on_delete=models.CASCADE)
    condition = models.IntegerField(default=1, choices=BOOK_CONDITIONS)
    with_student = models.BooleanField(default=False)
    ready_for_loan = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self._state.adding:
            self.book_id.physical = True
            if self.condition == 1 or self.condition == 3:
                self.book_id.inventory += 1
            if self.condition == 3:
                self.ready_for_loan = True
        else:
            original = PhysicalBook.objects.get(pk=self.pk)
            if original.condition != 2 and self.condition == 2:
                self.book_id.inventory -= 1
                self.book_id.stock_level -= 1
                self.ready_for_loan = False
            elif original.condition == 2 and self.condition == 3:
                self.book_id.inventory += 1
                self.book_id.stock_level += 1
                self.ready_for_loan = True
        self.book_id.save()

        super(PhysicalBook, self).save(*args, **kwargs)

    def remove(self, *args, **kwargs):
        if self.condition == 1 or self.condition == 3:
            self.book_id.inventory -= 1
            self.book_id.stock_level -= 1
            self.book_id.save()
        super(PhysicalBook, self).delete(*args, **kwargs)
    
    def damage(self, *args, **kwargs):
        if self.with_student:
            pass
        else:
            self.ready_for_loan = False
            self.conditon = 2
            self.book_id.inventory -= 1
            self.book_id.stock_level -= 1
            self.book_id.save()
            self.save()
    
        

    def __str__(self):
        return f'BLSBookID: {self.physical_id} - {self.book_id.title}'





class Book(AbstractModel):
    book_id = models.AutoField(primary_key=True)
    title = models.CharField(max_length=100, validators=[check_book_text])  
    author = models.CharField(max_length=100, validators=[check_book_text])
    isbn = models.CharField(max_length=100, validators=[
                            check_isbn])
    category = models.IntegerField(choices=BOOK_CATEGORIES)
    physical = models.BooleanField(default=True)
    ebook = models.BooleanField(default=True)
    file = models.FileField(upload_to='books/', blank=True, validators=[
                            FileExtensionValidator(['pdf'], 'incorrect File Type!')])
    stock_level = models.IntegerField(default=0, blank=True)
    inventory = models.IntegerField(default=0)
    description = models.CharField(max_length=1000, blank=True)
    cover = models.ImageField(upload_to='covers/', blank=True)
    in_stock = models.BooleanField(default=False)
    numofpages = models.IntegerField(default=10, blank=True)
    text = models.TextField(blank=True)
    audio = models.FileField(upload_to='audio/', blank=True)
    audio_version = models.BooleanField(default=False)

    def __str__(self):
        return self.title

    def text_extract(self):
        with pymupdf.open(self.file.path) as pdf:
            booktext = ''
            for page in pdf:
                pagetext = page.get_text()
                booktext += pagetext
            self.text = booktext
            print(booktext)
            self.save()

    def audio_maker(self):
        try:
            engine = pyttsx3.init()
            engine.save_to_file(self.text, f'{self.title}_{self.author}.mp3')
            engine.runAndWait()
            engine.stop()
            shutil.move(os.path.join(settings.BASE_DIR, f'{self.title}_{self.author}.mp3'), os.path.join(
                settings.MEDIA_ROOT, 'audio'))
            self.audio = os.path.join(
                settings.MEDIA_ROOT, 'audio', f'{self.title}_{self.author}.mp3')
            self.audio_version = True
            self.save()
        except Exception as exception:
            # to be handled
            admin_alert(
                'Audiobook error', f'Dear Admin, kindly see to the following error {exception}')

    def recommend_books(self):
        if len(Book.objects.all()) <= 1:
            return []
        else:
            all_reads = OnlineBookRead.objects.filter(book=self.book_id)
            all_reads = all_reads.exclude(nextbook=None)
            if len(all_reads) > 0:
                next_books = {}
                for read in all_reads:
                    if read.nextbook.book in next_books:
                        next_books[read.nextbook.book] += 1
                    else:
                        next_books[read.nextbook.book] = 1
                print(next_books)
                if self in next_books:
                    print('remv')
                    del next_books[self]
                print(next_books)

                if len(next_books) > 0:
                    top1 = max(next_books, key=next_books.get)
                    next_books[top1] = 0
                    top2 = max(next_books, key=next_books.get)
                    next_books[top2] = 0
                    top3 = max(next_books, key=next_books.get)
                    print(top1, top2, top3)
                    return list(set([top1, top2, top3]))
                else:
                    return list(Book.objects.filter(category=self.category).exclude(book_id=self.book_id).order_by('?')[:3])
            else:
                return list(Book.objects.filter(category=self.category).exclude(book_id=self.book_id).order_by('?')[:3])

    def check_stock_on_date(self, date, extension, loan_id):
        related_loans = Loan.objects.filter(book_id=self.book_id, active=True)
        avaliability = self.inventory
        # skip the extending loan, to account for it
        for loan in related_loans:
            if loan_id == None:
                pass
            else:
                if extension:
                    if loan.loan_id == loan_id:
                        continue

            start = datetime.combine(loan.start_date, datetime.min.time())
            end = datetime.combine(loan.end_date, datetime.min.time())
            date = datetime.combine(date, datetime.min.time())
            if start <= date <= end:
                print('ERRORCAUSER:', date)
                avaliability -= 1

        if avaliability > 0:
            return True
        else:
            return False

    def check_stock_indicator(self):
        related_loans = Loan.objects.filter(book_id=self.book_id, active=True)
        tomorrow = datetime.today() + timedelta(days=1)
        count = self.inventory
        for loan in related_loans:
            if loan.start_date <= datetime.today().date() <= loan.end_date:
                count -= 1
                continue

            if loan.start_date <= tomorrow.date() <= loan.end_date:
                count -= 1

        if count > 0:
            self.in_stock = True
            self.stock_level = count
        else:
            self.in_stock = False
            self.stock_level = 0



    def watermark(self):
        watermark_path = os.path.join(settings.BASE_DIR, 'static', 'watermark.png')
        if not os.path.exists(watermark_path):
            return  # skip watermarking if image not found
        original = pymupdf.open(self.file.path)
        for index in range(len(original)):
            page = original[index]
            rect = page.rect
            page.insert_image(
                rect, filename=watermark_path, overlay=True)

        original.save(self.file.path, incremental=True, encryption=0)

    def clean(self):
        existing = Book.objects.filter(isbn=self.isbn).exclude(pk=self.pk)
        if existing.exists():
            raise ValidationError({'isbn': "A book with this ISBN already exists."})
        
    def save(self, *args, **kwargs):
        self.check_stock_indicator()
        check_unique(self.isbn, self.book_id)
        # stock level indicates the number of books avaliable for loan for 1 day beginning today.
        if not self.file:
            self.ebook = False
        if self._state.adding:
            self.stock_level = 0
            self.inventory = 0
        
        if self.file and not self.file._committed:
            self.file.name = f'{self.title}_{self.author}.pdf'
            super(Book, self).save(*args, **kwargs)
            pdfobject = pymupdf.open(self.file.path)
            self.numofpages = len(pdfobject)
            pdf = pdfpck.convert_from_path(
                self.file.path, 400, poppler_path=POPPLER_PATH)

            dir_cov = os.path.join(settings.MEDIA_ROOT, 'covers')
            if not os.path.exists(dir_cov):
                os.makedirs(dir_cov)

            cover_path = os.path.join(
                dir_cov, f'{self.title}_{self.author}.jpg')
            pdf[0].save(cover_path, 'JPEG')
            self.cover = f'covers/{self.title}_{self.author}.jpg'
            if self.stock_level == 0:
                self.in_stock = False
            self.watermark()
        elif not self.file:
            self.cover = f'covers/ebook-not-avail.png'

            super(Book, self).save(*args, **kwargs)

        super(Book, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        try:
            if self.file:
                os.remove(self.file.path)
            if self.cover:
                os.remove(self.cover.path)
        except Exception as error:
            print(f'Book file deletion error: {error}')
            try:
                admin_alert('Book Deletion Error',
                            f'{error} occured while deleting {self.title} through self.delete')
            except Exception:
                pass  # Don't let email failure block deletion

        super(Book, self).delete(*args, **kwargs)

    def remove(self, *args, **kwargs):
        try:
            if self.file:
                os.remove(self.file.path)
            if self.cover:
                os.remove(self.cover.path)
        except Exception as error:
            print(f'Book file removal error: {error}')
            try:
                admin_alert('Book Deletion Error',
                            f'{error} occured while deleting {self.title} through self.remove')
            except Exception:
                pass  # Don't let email failure block deletion
        super(Book, self).delete(*args, **kwargs)


class BLSUser(AbstractUser):
    def is_student(self):
        return True if self.groups.filter('Students').exists() else False

    def is_admin(self):
        return True if self.groups.filter(name='Admins').exists() else False

    def is_staff_member(self):
        if self.groups.filter(name='Librarians').exists():
            return True
        else:
            if self.groups.filter(name='Admins').exists():
                return True
            return False



    def overdue_penalty(self, loan):
        if Penalty.objects.filter(loan_id=loan, reason_overdue=True, paid=False).exists():
            the_penalty = Penalty.objects.get(
                loan_id=loan, reason_overdue=True)
            the_penalty.amount += 100
            the_penalty.save()
        else:
            the_penalty = Penalty.objects.create(
                user_id=self, loan_id=loan, amount=1, reason_overdue=True)
            the_penalty.save()

        return the_penalty.amount 
    def ban(self):
        self.banned = True
        self.save()

    def unban(self):
        self.banned = False
        self.save()  




    banned = models.BooleanField(default=False)


class LoanIssuanceNotes(AbstractModel):
    id = models.AutoField(primary_key=True)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    issued = models.BooleanField()
    user_id = models.ForeignKey(BLSUser, on_delete=models.CASCADE)
    physicalbook = models.ForeignKey(
        PhysicalBook, on_delete=models.CASCADE, null=True)
    start_date = models.DateField()
    end_date = models.DateField()
    reason = models.CharField(max_length=1000)
    loan_id = models.ForeignKey(
        'Loan', on_delete=models.CASCADE, blank=True, null=True)
    flag = models.IntegerField()


class Loan(AbstractModel):
    status = models.CharField(
        max_length=100, blank=True, default='Awaiting Collection.')
    loan_id = models.AutoField(primary_key=True)
    book_id = models.ForeignKey(Book, on_delete=models.CASCADE)
    user_id = models.ForeignKey(BLSUser, on_delete=models.CASCADE)
    duration = models.IntegerField(
        default=7, validators=[MaxValueValidator(7)])
    renewed = models.BooleanField(default=False)
    start_date = models.DateField(validators=[check_future])
    end_date = models.DateField(validators=[check_future], blank=True)
    active = models.BooleanField(default=False)
    physicalbook = models.ForeignKey(
        PhysicalBook, on_delete=models.CASCADE, blank=True, null=True)
    overdue = models.BooleanField(default=False)
    custody = models.BooleanField(default=False)
    early_return = models.BooleanField(default=False)
    rejected = models.BooleanField(default=False)
    # custody dictates whether the beneficiary has custody of the book

    def extension_eligibility(self, requested_days, *args, **kwargs):
        if self.renewed:
            return False, 0, 'Book has already been renewed once.'

        if datetime.today().date() < self.end_date:
            reason = 'Book is not eligible for extension. Book is not at end of initial loan, return when done.'
            return False, 2, reason

        proposed_start = datetime.combine(self.end_date, datetime.min.time())
        end = self.end_date + timedelta(days=requested_days)
        proposed_end = datetime.combine(end, datetime.min.time())
        user_loans = Loan.objects.filter(
            user_id=self.user_id, book_id=self.book_id, active=True)

        stock = True
        days_between = [proposed_start + timedelta(days=n)
                        for n in range((proposed_end - proposed_start).days + 1)]
        if len(days_between) - 1 > 7:
            reason = 'Extension duration cannot be more than 7 days.'
            return False, 4, reason

        for day in days_between:
            extension = True
            instock = Book.check_stock_on_date(
                self.book_id, day, extension, self.loan_id)
            if not instock:
                stock = False
                reason = f'Stock Not available for duration of requested loan. Out of stock on: {day.date()}'
                break

        if not instock:
            self.rejected = True
            return False, 1, reason

        self.active = True
        reason = 'User is eligible to loan this book.'
        return True, 3, reason

    def issuance_eligibility(self, requesteddays, *args, **kwargs):
        # FLAG EXPLANATION: 1 is not instock, 2 is within 2 weeks cooling period, 3 is other, 4 is eligible, 5 is already attempted to loan in these dates.
        userloans = Loan.objects.filter(
            user_id=self.user_id, book_id=self.book_id, active=True)
        proposed_start = datetime.combine(self.start_date, datetime.min.time())
        proposed_end = datetime.combine(self.end_date, datetime.min.time())
        duplicateflag = False
        if proposed_end < proposed_start:
            self.rejected = True
            reason = 'End date cannot be before start date.'
            return False, 6, reason
        
        for loan in userloans:
            existing_start = datetime.combine(
                loan.start_date, datetime.min.time())
            existing_end = datetime.combine(loan.end_date, datetime.min.time())

            if existing_start == proposed_start and existing_end == proposed_end:
                self.rejected = True
                reason = 'User has already attempted to loan this book.'
                return False, 5, reason
        stock = True

        days_between = [proposed_start + timedelta(days=n)
                        for n in range((proposed_end - proposed_start).days + 1)]
        if len(days_between) - 1 > 7:
            reason = 'Loan duration cannot be more than 7 days.'
            return False, 0, reason
        for day in days_between:
            extension = False
            instock = Book.check_stock_on_date(
                self.book_id, day, extension, None)
            if not instock:
                stock = False
                reason = f'Stock Not available for duration of requested loan. Out of stock on: {day.date()}'
                break

        if not stock:
            self.rejected = True
            return False, 1, reason


        problem_flag = False
        two_week_loans = Loan.objects.filter(
            user_id=self.user_id, book_id=self.book_id, rejected=False)
        for loan in two_week_loans:
            loan_end = datetime.combine(loan.end_date, datetime.min.time())
            low_threshold = proposed_start - timedelta(days=14)
            if low_threshold < loan_end < proposed_start:
                self.rejected = True
                problem_flag = True
                reason = 'User is within the 2-week cooling period and hence is not eligible to loan this book.'
                return False, 2, reason
#
        if not problem_flag:
            self.active = True
            if len(userloans) == 0:
                reason = 'User is eligible to loan this book. No conditions checked, as no loans existing.'
                return True, 4, reason
            else:
                reason = 'User is eligible to loan this book.'
                return True, 4, reason

    def save(self, *args, **kwargs):
        if self.rejected:
            self.active = False

        request = kwargs.pop('request', 0)
        if self._state.adding:
            book = self.book_id
            if request and request.path.startswith('/admin/'):
                self.end_date = self.start_date + timedelta(days=self.duration)
            else:
                self.duration = (self.end_date - self.start_date).days

            eligible, flag, reason = self.issuance_eligibility(
                requesteddays=self.duration)
            reasons = ['Loan duration cannot exceed 7 days.',
                       'Insufficient stock available for the requested period.',
                       'User is within the 2-week cooling-off period.',
                       'Reactivating an existing loan.',
                       'Loan request approved successfully.',
                       'Duplicate loan request detected.',
                       'end date must be after start date']
            if eligible:
                self.active = True
                self.book_id.save()
            else:
                self.active = False
                self.rejected = True
                if request and request.path.startswith('/admin/'):
                    messages.set_level(request, messages.WARNING)
                    messages.warning(request, reasons[flag])

            super(Loan, self).save(*args, **kwargs)
            LoanIssuanceNotes.objects.create(flag=flag, issued=self.active, user_id=self.user_id, book=self.book_id,
                                             start_date=self.start_date, end_date=self.end_date, reason=reason, loan_id=self)
            book.save()
        else:
            super(Loan, self).save(*args, **kwargs)
            self.book_id.save()

    def renew(self, *args, **kwargs):
        eligible, flag, reason = self.extension_eligibility(
            requested_days=7, loan_id=self.loan_id)

        if eligible:
            self.renewed = True
            self.end_date = self.end_date + timedelta(days=7)
        else:
            pass
            # messages.warning(self.request, reason)
        super(Loan, self).save(*args, **kwargs)

    def delete(self, *args, **kwargs):
        book = self.book_id
        if self.physicalbook:
            self.physicalbook.with_student = False
            self.physicalbook.ready_for_loan = True
        super(Loan, self).delete(*args, **kwargs)
        book.save()

    def return_book(self, *args, **kwargs):
        self.active = False
        self.custody = False
        self.physicalbook.with_student = False
        self.physicalbook.ready_for_loan = True
        self.physicalbook.save()
        super(Loan, self).save(*args, **kwargs)

    def collect(self, *args, **kwargs):
        avaliables = PhysicalBook.objects.filter(
            book_id=self.book_id, ready_for_loan=True)
        self.physicalbook = avaliables[0]
        super(Loan, self).save(*args, **kwargs)
        self.custody = True
        self.status = 'Collected. In Progress.'
        self.physicalbook.ready_for_loan = False
        self.physicalbook.with_student = True
        self.physicalbook.save()
        self.book_id.save()
        super(Loan, self).save(*args, **kwargs)

    def __str__(self):
        return f'LOAN: {self.user_id} - {self.book_id}'


class Damage(AbstractModel):

    user_id = models.ForeignKey(BLSUser, on_delete=models.CASCADE, blank=True)
    physicalbook = models.ForeignKey(
        PhysicalBook, on_delete=models.CASCADE, blank=True)
    loan_id = models.ForeignKey(Loan, on_delete=models.CASCADE)
    student_comments = models.CharField(max_length=1000)
    liabile = models.BooleanField(default=False)
    penalty_issued = models.BooleanField(default=False)
    date = models.DateField()
    resolved = models.BooleanField(default=False)
    damage_id = models.AutoField(primary_key=True)
    category = models.IntegerField(default=1, choices=DAMAGE_OPTIONS)
    admin_comments = models.CharField(max_length=1000, blank=True)

    def __str__(self):
        return f'Damage {self.damage_id} ({self.user_id}) - PB:{self.physicalbook}'

    def save(self, *args, **kwargs):
        if self._state.adding:
            self.user_id = self.loan_id.user_id
            self.physicalbook = self.loan_id.physicalbook
        super(Damage, self).save(*args, **kwargs)


class Bookmark(AbstractModel):
    user_id = models.ForeignKey(BLSUser, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    bookmark_id = models.AutoField(primary_key=True)
    page_number = models.IntegerField()
    comments = models.CharField(max_length=1000)

    def __str__(self):
        return f'Bookmark {self.bookmark_id} ({self.user_id}) - {self.book} - Page {self.page_number}'


class Review(AbstractModel):

    user_id = models.ForeignKey(BLSUser, on_delete=models.CASCADE)
    book = models.ForeignKey(Book, on_delete=models.CASCADE)
    review_id = models.AutoField(primary_key=True)
    comments = models.CharField(max_length=1000)
    revnote = models.ForeignKey(
        'ReviewNote', on_delete=models.CASCADE, blank=True)
    see = models.BooleanField(default=True)

    def __str__(self):
        return f'Review {self.review_id} ({self.user_id}) - {self.book}'

    def checks(self):
        url = f'https://api.api-ninjas.com/v1/profanityfilter?text={self.comments}'
        headers = {
            'x-api-key': API_NINJA_KEY
        }

        if len(self.comments) == 0 or self.comments.isspace():
            revnote = ReviewNote.objects.create(
                user_id=self.user_id, comments='Empty review', blocked=True)
            return False, revnote
        
        try:
            profcheck = requests.get(url, headers=headers)
            print(profcheck)
            profcheck.raise_for_status()
        except Exception as error:
            print('API Error')
            revnote = ReviewNote.objects.create(
                user_id=self.user_id, comments='Internal Server Error - Contact Librarian', blocked=True)
            admin_alert('APIError - Profanity Check',
                        'Profanity Check API Error {error}')
            return False, revnote

        # email checking procdure
        if len(re.findall(r'[A-Za-z0-9._-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,6}', self.comments)) > 0:
            revnote = ReviewNote.objects.create(
                user_id=self.user_id, comments='Contact detail sharing is forbidden', blocked=True)
            return False, revnote

        if len(list(phonenumbers.PhoneNumberMatcher(self.comments, 'PK'))) > 0:
            revnote = ReviewNote.objects.create(
                user_id=self.user_id, comments='Contact detail sharing is forbidden.', blocked=True)
            return False, revnote

        if len(list(phonenumbers.PhoneNumberMatcher(self.comments, 'GB'))) > 0:
            revnote = ReviewNote.objects.create(
                user_id=self.user_id, comments='Contact detail sharing is forbidden.', blocked=True)
            return False, revnote

        profdata = profcheck.json()
        if profdata['has_profanity'] == True:
            revnote = ReviewNote.objects.create(
                user_id=self.user_id, comments='Profanity is forbidden.', blocked=True)
            return False, revnote
        else:
            revnote = ReviewNote.objects.create(
                user_id=self.user_id, comments='pass', blocked=False)
            return True, revnote

    def save(self, *args, **kwargs):
        if self._state.adding:
            check, note = self.checks()
            if check:
                self.revnote = note
                self.see = True
                super(Review, self).save(*args, **kwargs)
            else:
                self.revnote = note
                self.see = False
                super(Review, self).save(*args, **kwargs)


class ReviewNote(AbstractModel):
    user_id = models.ForeignKey(BLSUser, on_delete=models.CASCADE)
    note_id = models.AutoField(primary_key=True)
    comments = models.CharField(max_length=1000)
    blocked = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.user_id} noted - {self.comments}'


class Penalty(AbstractModel):
    # dont want top 2 fields to appear on form, till saved.
    user_id = models.ForeignKey(BLSUser, on_delete=models.CASCADE, blank=True)
    physicalbook = models.ForeignKey(
        PhysicalBook, on_delete=models.CASCADE, blank=True)
    damage_id = models.ForeignKey(Damage, on_delete=models.CASCADE, blank=True, null=True)
    loan_id = models.ForeignKey(Loan, on_delete=models.CASCADE, blank=True, null=True)
    issuance_date = models.DateField()
    paid = models.BooleanField(default=False)
    pay_method = models.IntegerField(default=1, choices=PAYMENT_METHODS)
    penalty_id = models.AutoField(primary_key=True)
    amount = models.IntegerField(default=1)
    admin_comments = models.CharField(max_length=1000, blank=True)
    reason_overdue = models.BooleanField(default=False)

    def __str__(self):
        return f'{self.penalty_id}'

    def save(self, *args, **kwargs):
        print('in save func')
        if self.paid:
            print('in self paid')
            print(self.damage_id.resolved)
            self.damage_id.resolved = True
            self.damage_id.save()
        else:
            self.damage_id.penalty_issued = True
            self.damage_id.save()

        if self._state.adding:
            self.physicalbook = self.damage_id.physicalbook
            self.user_id = self.damage_id.user_id

        super(Penalty, self).save(*args, **kwargs)


class OnlineBookRead(AbstractModel):
    user = models.ForeignKey(BLSUser, on_delete=models.CASCADE)
    book = models.ForeignKey(
        Book, on_delete=models.CASCADE, related_name='book')
    category = models.IntegerField(choices=BOOK_CATEGORIES)
    servedpdf = models.FileField(upload_to='servedpdfs/', blank=True, validators=[
                                 FileExtensionValidator(['pdf'], 'incorrect File Type!')])
    nextbook = models.ForeignKey(
        'OnlineBookRead', on_delete=models.CASCADE, blank=True, null=True, related_name='nextread')

    def save(self, *args, **kwargs):
        if self._state.adding:
            self.category = self.book.category
        super(OnlineBookRead, self).save(*args, **kwargs)
