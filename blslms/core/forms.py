from django import forms
from .models import *
from datetime import datetime
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from core.constants import *
import requests
from core.validators import *


class BookFilter(forms.Form):
    category = forms.ChoiceField(choices=[], required=False)
    author = forms.ChoiceField(choices=[], required=False)
    ebook = forms.BooleanField(required=False, label='Avaliable as eBook')
    instock = forms.BooleanField(required=False, label='Only books inStock')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        categories = [('', 'All')] + [(id, name) for id, name in BOOK_CATEGORIES]
        authors = [('', 'All')] + [(name, name) for name in Book.objects.values_list('author', flat=True).distinct()]
        self.fields['category'].choices = categories
        self.fields['author'].choices = authors

class LoanForm(forms.Form):
    start_date = forms.DateField(required=True, label='Choose start date: ', widget=forms.DateInput(attrs={'type': 'date'}), validators=[check_future])
    end_date = forms.DateField(required=True, label='Choose end date: ', widget=forms.DateInput(attrs={'type': 'date'}), validators=[check_future])

class ExtendForm(forms.Form):
    days = forms.IntegerField(min_value=1, max_value=14, label='Number of days to extend: ')

class ReportDamageForm(forms.Form):
    category = forms.ChoiceField(choices=DAMAGE_OPTIONS)
    student_comments = forms.CharField()

class BookReviewForm(forms.Form):
    comments = forms.CharField(widget=forms.Textarea, max_length=250, validators=[check_not_empty])


class BookmarkForm(forms.Form):
    page = forms.IntegerField(min_value=1)
    comments = forms.CharField(widget=forms.Textarea, max_length=250)

    
    

class BookAdminForm(forms.ModelForm):
    title = forms.CharField(
        max_length=100,
        required=False,
        label='Book Title:',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    author = forms.CharField(
        max_length=100,
        required=False,
        label='Book Author:',
        widget=forms.TextInput(attrs={'class': 'form-control'})
    )
    isbn = forms.CharField(
        max_length=13,
        required=True,
        label='ISBN:',
        widget=forms.TextInput(attrs={'class': 'form-control'}),
    )
    category = forms.ChoiceField(
        choices=BOOK_CATEGORIES,
        label='Book Category:',
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    file = forms.FileField(
        label='Upload Book PDF File:',
        widget=forms.FileInput(attrs={'class': 'form-control'}),
        required=False
    )
    description = forms.CharField(
        max_length=1000,
        required=False,
        label='Description:',
        widget=forms.Textarea(attrs={'class': 'form-control'})
    )



    


