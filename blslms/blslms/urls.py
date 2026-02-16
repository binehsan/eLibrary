"""
URL configuration for blslms project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.1/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
# In your_app/urls.py
from django.urls import path, include
from django.contrib import admin
from core.views import *
from django.conf import settings
from django.conf.urls.static import static

admin.site.site_header = 'BLS eLibrary'
admin.site.site_title = 'BLS eLibrary'
admin.site.index_title = 'Dashboard - BLS'
urlpatterns = [
    path('admin/', admin.site.urls),
    path('student/books', student_books, name='student_books'),
    path('books', books, name='books'),
    path('book/<int:book_id>/', book, name='book'), #book
    path('student_books', student_books, name='student_books'),
    path('confirm_loan/<int:book_id>/', confirm_loan, name='confirm_loan'),
    path('loan_executed/<int:book_id>', loan_executed, name='loan_executed'),
    path('loanexecuted/<int:book_id>/<int:issuance_id>', loan_executed, name='loan_executed'),
    path('loan/<int:loan_id>', loan, name='loan'),
    path('accounts/login/', CustomLoginView.as_view(), name='account_login'),
    path('accounts/', include('allauth.urls')),
    path('dashboard/', dashboard, name='dashboard'),
    path('admin/dashboard/', admin_dashboard, name='admin_dashboard'),
    path('student/dashboard/', student_dashboard, name='student_dashboard'),
    path('report_executed/<int:loan_id>', report_executed, name='report_executed'),
    path('report_damage/<int:loan_id>', report_damage, name='report_damage'),
    path('review/<int:book_id>', review, name='review'),
    path('review_executed/<int:book_id>', review_executed, name='review_executed'),
    path('create_bookmark/<int:book_id>', create_bookmark, name='create_bookmark'),
    path('bookmark_executed/<int:book_id>', bookmark_executed, name='bookmark_executed'),
    path('profile/<str:username>', profile, name='profile'),  
    path('penalty/<int:penalty_id>', penalty, name='penalty'),
    path('delete_review/<int:review_id>', delete_review, name='delete_review'),
    path('banned', banned, name='banned'),
    path('delete_bookmark/<int:bookmark_id>', delete_bookmark, name='delete_bookmark'),
    path('extend/<int:loan_id>', extend, name='extend'),
    path('extension_issued/<int:loan_id>', extension_issued, name='extension_issued'),
    # Include other URLs as needed
]



if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
