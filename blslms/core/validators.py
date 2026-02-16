from datetime import datetime
from django.core.exceptions import ValidationError
import re

def check_future(date: datetime):
    today = datetime.combine(datetime.today(), datetime.min.time())
    date = datetime.combine(date, datetime.min.time())
    if date < today:
        raise ValidationError('Date cannot be in the past!')

def check_isbn(isbn: int):
    if re.search('[a-z]+', str(isbn)) != None or re.search('[A-Z]+', str(isbn)) != None:
        raise ValidationError('ISBN must be a number!')
    if len(isbn) > 13 or len(isbn) < 10:
        raise ValidationError('ISBN must be between 10 and 13')
    
    if not isbn.isdigit():
        raise ValidationError('ISBN must be a number.') 
    
def check_isbn_task(isbn):
    if len(str(isbn)) > 13:
        return False
    
    if not str(isbn).isdigit():
        return False

    return True

def check_book_text(value): 
    if str(value).isspace():
        raise ValidationError('This field must be a string!')
    
    if len(value) < 1:
        raise ValidationError('This field cannot be empty!')
    
    if str(value).isdigit():
        raise ValidationError('This field cannot be a number!')
    
def check_not_empty(value):
    pass
    
def check_end_future(date: datetime, loan):
    start = datetime.combine(loan.start_date, datetime.min.time())
    end = datetime.combine(loan.end_date, datetime.min.time())
    if end < start:
        raise ValidationError('End date cannot be before start date!')

