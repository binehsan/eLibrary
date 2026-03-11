from django.shortcuts import render
from pathlib import Path
import os
import datetime
import logging
from django.shortcuts import redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import Group
from allauth.account.views import LoginView
from django.urls import reverse
from .models import *
from .forms import *
import pymupdf
import random
from django.contrib.auth import logout

BASE_DIR = Path(__file__).resolve().parent.parent
logger = logging.getLogger('blslms')


# ── Error codes reference ──────────────────────────────────
# BLS-E001  Book not found
# BLS-E002  Loan not found
# BLS-E003  Penalty not found
# BLS-E004  Review not found
# BLS-E005  Bookmark not found
# BLS-E006  User not found
# BLS-E007  Unauthorised access
# BLS-E008  Invalid form submission
# BLS-E009  Out-of-range page number (bookmark)
# BLS-E010  No physical copies available (collect)
# BLS-E011  Internal / unexpected error
# ────────────────────────────────────────────────────────────

def _error(request, code, message, status=400):
    """Render the error template with a code and message, and log it."""
    logger.warning('ERROR_PAGE | code=%s | user=%s | path=%s | msg=%s',
                   code, getattr(request, 'user', '?'), request.path, message)
    return render(request, 'error.html', {'code': code, 'message': message}, status=status)


class CustomLoginView(LoginView):
    def form_valid(self, form):
        response = super().form_valid(form)
        user = self.request.user
        print(f'User {user.username} authenticated: {user.is_authenticated}')
        return response
    # aic

    def form_invalid(self, form):
        print('Login failed due to errors:')
        print(form.errors)
        logout(self.request)
        return self.render_to_response(self.get_context_data(form=form))


@login_required
def dashboard(request):
    user = request.user
    if user.is_staff_member():
        return redirect('admin:index')
    else:
        if user.banned:
            return redirect('banned')
        else:

            return redirect('student_dashboard')


@login_required
def admin_dashboard(request):
    return render(request, 'admin_dashboard.html')


@login_required
def banned(request):
    logout(request)
    return render(request, 'banned.html')


@login_required
def student_dashboard(request):
    category_frequency = {}
    users_read_books = OnlineBookRead.objects.filter(user_id=request.user)

    if len(users_read_books) > 0:
        for readbook in users_read_books:
            if readbook.book.category in category_frequency:
                category_frequency[readbook.book.category] += 1
            else:
                category_frequency[readbook.book.category] = 1

        liked_category1 = max(category_frequency, key=category_frequency.get)
        category_frequency[liked_category1] = 0
        liked_category2 = max(category_frequency, key=category_frequency.get)
        cat1books = list(Book.objects.filter(
            category=liked_category1).order_by('?'))
        cat2books = list(Book.objects.filter(
            category=liked_category2).order_by('?'))
        books = cat1books[:3] + cat2books[:3]

        books = list(set(books))

    else:
        books = list(Book.objects.all().order_by('?'))[:6]

    loanedbooks = Loan.objects.filter(user_id=request.user, active=True)
    penalty = True if len(Penalty.objects.filter(
        user_id=request.user, paid=False)) > 0 else False
    penaltyamount = len(Penalty.objects.filter(
        user_id=request.user, paid=False))
    user = request.user

    return render(request, 'student_dashboard.html', {'user': user, 'books': books, 'loanedbooks': loanedbooks, 'penalty': penalty, 'penaltyamount': penaltyamount})


@login_required
def books(request):


    books = Book.objects.all()
    filterform = BookFilter(request.GET or None)

    if filterform.is_valid():
        if filterform.cleaned_data['category']:
            books = books.filter(category=filterform.cleaned_data['category'])
        if filterform.cleaned_data['author']:
            books = books.filter(author=filterform.cleaned_data['author'])
        if filterform.cleaned_data['ebook']:
            books = books.filter(ebook=True)
        if filterform.cleaned_data['instock']:
            books = books.filter(in_stock=True)
        
    print(books)
    context = {'books': books, 'form': filterform}
    return render(request, 'books.html', context)


@login_required
def book(request, book_id):
    if not Book.objects.filter(book_id=book_id).exists():
        return _error(request, 'BLS-E001', 'Book not found.', status=404)
    user = request.user
    previousreads = OnlineBookRead.objects.filter(
        user_id=user).order_by('-creation_date')
    lastread = previousreads[0] if len(previousreads) > 0 else None
    thisread = OnlineBookRead.objects.create(user_id=user.id, book_id=book_id)
    if lastread:
        lastread.nextbook = thisread
        print(f'prev: {lastread.book} --> {lastread.nextbook.book}')
        lastread.save()

    book = get_object_or_404(Book, book_id=book_id)
    top_books = book.recommend_books()
    allrev = list(Review.objects.filter(book_id=book_id, see=True))
    random.shuffle(allrev)
    bookmarks = Bookmark.objects.filter(book_id=book_id, user_id=request.user)
    if not book.file:
        no_avail_image = os.path.join(
            BASE_DIR, 'core', 'static', 'ebook-not-avail.png')
        return render(request, 'book.html', {'recommended_books': top_books, 'book': book, 'reviews': allrev[:3], 'noavailcover': no_avail_image, 'bookmarks': bookmarks, 'hasbook': False})
    else:
        # temporarily copying pdf
        url = os.path.join(BASE_DIR, book.file.path)
        temp_path = os.path.join(
            BASE_DIR, 'core', 'temps', f'temp_{user.username}_{book.title}_{random.randint(1, 1000)}.pdf')
        servepdf = pymupdf.open(book.file.path)
        for page in servepdf:
            dimensions = page.rect
            append_position = pymupdf.Point(35, dimensions.y1 - 10)

            page.insert_text(
                append_position, f'(BLS eLibrary): Accessed by: {user.username} on {datetime.now()}', fontsize=5, color=(0, 0, 0))

        servepdf.save(temp_path)

        ebook = OnlineBookRead(user=user, book=book)
        # aic
        with open(temp_path, 'rb') as pdf_file:
            ebook.servedpdf.save(
                f'temp_{user.username}_{book.title}.pdf', (pdf_file))

        ebook.save()

        top_books = book.recommend_books()
        return render(request, 'book.html', {'recommended_books': top_books, 'book': book, 'ebook': ebook, 'reviews': allrev[:3], 'url': url, 'bookmarks': bookmarks, 'hasbook': True})


@login_required
def student_books(request):
    user = request.user
    loans = Loan.objects.filter(user_id=user, active=True)
    books_temp = [loan.book_id for loan in loans]
    books = Book.objects.filter(title__in=books_temp)
    return render(request, 'student_books.html', {'books': books, 'loans': loans, 'form': BookFilter})


@login_required
def confirm_loan(request, book_id, **kwargs):
    user = request.user
    book = get_object_or_404(Book, book_id=book_id)
    location = 'BLS Central Library'
    return render(request, 'confirm_loan.html', {'form': LoanForm, 'book': book, 'user': user, 'location': location})


@login_required
def loan(request, loan_id):
    loan = Loan.objects.filter(loan_id=loan_id)
    if not loan.exists():
        return _error(request, 'BLS-E002', 'Loan not found.', status=404)
    else:
        loan = loan[0]
    if request.user == loan.user_id:
        if loan.active and loan.start_date > datetime.now().date():
            if loan.custody:
                loan.status = 'Collected, In Progress'
            else:
                loan.status = 'Awaiting Collection'
        else:
            loan.status = 'Completed'

        return render(request, 'loan.html', {'loan': loan})
    else:
        return _error(request, 'BLS-E007', 'You are not authorised to view this loan.', status=403)


@login_required
def report_damage(request, loan_id):
    user = request.user
    loan = Loan.objects.get(loan_id=loan_id)
    return render(request, 'report_damage.html', {'form': ReportDamageForm, 'loan': loan, 'user': user})


@login_required
def profile(request, username):
    user = BLSUser.objects.filter(username=username)
    if not user.exists():
        return _error(request, 'BLS-E006', 'User not found.', status=404)
    user = user[0]
    read_books = OnlineBookRead.objects.filter(user_id=user)
    title_frequency = {}
    books = []
    if len(read_books) > 0:
        for readbook in read_books:
            if readbook.book.title in title_frequency:
                title_frequency[readbook.book.title] += 1
            else:
                title_frequency[readbook.book.title] = 1

        top_book1 = max(title_frequency, key=title_frequency.get)
        title_frequency[top_book1] = 0
        top_book2 = max(title_frequency, key=title_frequency.get)
        books.append(Book.objects.get(title=top_book1))
        books.append(Book.objects.get(title=top_book2))

    if len(books) > 0:
        hasbooks = True
    else:
        hasbooks = False

    isuser = True if request.user == user else False
    penalities = Penalty.objects.filter(user_id=user, paid=False)
    reviews = Review.objects.filter(user_id=user, see=True)
    haspenalties = True if len(penalities) > 0 else False

    bookmarks = Bookmark.objects.filter(user_id=user)
    if len(bookmarks) > 0:
        hasbookmarks = True
    else:
        hasbookmarks = False

    return render(request, 'profile.html', {'hasbookmarks': hasbookmarks, 'bookmarks': bookmarks, 'hasbooks': hasbooks, 'isuser': isuser, 'books': books, 'user': user, 'penalties': penalities, 'haspenalties': haspenalties, 'reviews': reviews})


@login_required
def penalty(request, penalty_id):
    penalty = Penalty.objects.filter(penalty_id=penalty_id)
    if not penalty.exists():
        return _error(request, 'BLS-E003', 'Penalty not found.', status=404)
    else:
        penalty = penalty[0]
    return render(request, 'penalty.html', {'penalty': penalty})


@login_required
def delete_review(request, review_id):
    review = Review.objects.filter(review_id=review_id)
    if not review.exists():
        return _error(request, 'BLS-E004', 'Review not found.', status=404)
    else:
        review = review[0]
    review.delete()
    return render(request, 'delete_review.html')


@login_required
def delete_bookmark(request, bookmark_id):
    bookmark = Bookmark.objects.filter(bookmark_id=bookmark_id)
    if not bookmark.exists():
        return _error(request, 'BLS-E005', 'Bookmark not found.', status=404)
    else:
        bookmark = bookmark[0]
    if bookmark.user_id != request.user:
        return _error(request, 'BLS-E007', 'You are not authorised to delete this bookmark.', status=403)
    bookmark.delete()
    return render(request, 'delete_bookmark.html')


@login_required
def review(request, book_id):
    if not Book.objects.filter(book_id=book_id).exists():
        return _error(request, 'BLS-E001', 'Book not found.', status=404)
    
    user = request.user
    book = Book.objects.get(book_id=book_id)
    return render(request, 'writereview.html', {'form': BookReviewForm, 'book': book, 'user': user})


@login_required
def review_executed(request, book_id):
    if not Book.objects.filter(book_id=book_id).exists():
        return _error(request, 'BLS-E001', 'Book not found.', status=404)
    if request.method == 'POST':
        form = BookReviewForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
        else:
            data = {'comments': ''}
    else:
        form = LoanForm()

    comments = data['comments']
    book = Book.objects.get(book_id=book_id)
    user = request.user
    newreview = Review.objects.create(
        book_id=book_id, comments=comments, user_id=user)
    success = True if not newreview.revnote.blocked else False
    return render(request, 'review_executed.html', {'book': book, 'user': user, 'success': success, 'reason': newreview.revnote.comments})


@login_required
def report_executed(request, loan_id):
    if not Loan.objects.filter(loan_id=loan_id).exists():
        return _error(request, 'BLS-E002', 'Loan not found.', status=404)
    if request.method == 'POST':
        form = ReportDamageForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
    else:
        form = ReportDamageForm()

    print(data)
    date = datetime.now()
    student_comments = data['student_comments']
    category = data['category']
    loan = Loan.objects.get(loan_id=loan_id)
    book = Book.objects.get(book_id=loan.book_id.book_id)
    user = request.user
    Damage.objects.create(loan_id=loan, category=category, student_comments=student_comments,
                          date=date, physicalbook=loan.physicalbook, user_id=user)
    return render(request, 'report_executed.html', {'loan': loan, 'user': user})


@login_required
def loan_executed(request, book_id):
    if not Book.objects.filter(book_id=book_id).exists():
        return _error(request, 'BLS-E001', 'Book not found.', status=404)
    
    if request.method != 'POST':
        return redirect('confirm_loan', book_id=book_id)

    book = Book.objects.get(book_id=book_id)
    user = request.user
    location = 'BLS Central Library'

    form = LoanForm(request.POST)
    if not form.is_valid():
        return render(request, 'confirm_loan.html', {'form': form, 'book': book, 'user': user, 'location': location, 'message': 'Invalid date'})

    data = form.cleaned_data
    loan = Loan.objects.create(
        user_id=user,
        book_id=book,
        start_date=data['start_date'],
        end_date=data['end_date'],
    )
    note = LoanIssuanceNotes.objects.filter(loan_id=loan.loan_id).first()
    success = note.issued if note else False
    reason = note.reason if note else 'Loan request could not be processed.'

    return render(request, 'loan_executed.html', {'book': book, 'success': success, 'reason': reason})


@login_required
def create_bookmark(request, book_id):
    if not Book.objects.filter(book_id=book_id).exists():
        return _error(request, 'BLS-E001', 'Book not found.', status=404)
    user = request.user
    book = get_object_or_404(Book, book_id=book_id)
    return render(request, 'create_bookmark.html', {'form': BookmarkForm, 'book': book, 'user': user})


@login_required
def bookmark_executed(request, book_id):
    if not Book.objects.filter(book_id=book_id).exists():
        return _error(request, 'BLS-E001', 'Book not found.', status=404)
    if request.method != 'POST':
        return redirect('create_bookmark', book_id=book_id)

    form = BookmarkForm(request.POST)
    if not form.is_valid():
        book = Book.objects.get(book_id=book_id)
        return render(request, 'create_bookmark.html', {'form': form, 'book': book, 'user': request.user, 'message': 'Invalid bookmark details.'})

    data = form.cleaned_data
    book = Book.objects.get(book_id=book_id)
    user = request.user
    page = data['page']
    comments = data['comments']
    if page > book.numofpages:
        success = False
        bookmark = None
    else:
        success = True
        bookmark = Bookmark.objects.create(
            book=book, user_id=user, page_number=page, comments=comments)
    return render(request, 'bookmarkexecuted.html', {'book': book, 'user': user, 'bookmark': bookmark, 'success': success})


@login_required
def extend(request, loan_id):
    if not Loan.objects.filter(loan_id=loan_id).exists():
        return _error(request, 'BLS-E002', 'Loan not found.', status=404)
    user = request.user
    loan = Loan.objects.get(loan_id=loan_id)
    book = Book.objects.get(book_id=loan.book_id.book_id)
    return render(request, 'extend.html', {'form': ExtendForm, 'loan': loan, 'book': book, 'user': user, })


@login_required
def extension_issued(request, loan_id):
    if not Loan.objects.filter(loan_id=loan_id).exists():
        return _error(request, 'BLS-E002', 'Loan not found.', status=404)

    loan = Loan.objects.get(loan_id=loan_id)
    book = Book.objects.get(book_id=loan.book_id.book_id)

    if request.method != 'POST':
        return redirect('extend', loan_id=loan_id)

    form = ExtendForm(request.POST)
    if not form.is_valid():
        return render(request, 'extend.html', {'form': form, 'book': book, 'loan': loan, 'message': 'Invalid date'})

    days = form.cleaned_data['days']
    eligible, flag, reason = loan.extension_eligibility(requested_days=days)
    reasons = ['already renewed', 'outofstock',
               'not at end of loan', 'allowed', 'morethan7']
    if eligible:
        loan.end_date = loan.end_date + timedelta(days=days)
        loan.renewed = True
        loan.save()
        success = True
    else:
        success = False

    reason = reasons[flag]
    return render(request, 'extensionissued.html', {'book': book, 'success': success, 'reason': reason})
