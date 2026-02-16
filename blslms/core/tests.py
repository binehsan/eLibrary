from django.test import TestCase, Client
from django.urls import reverse
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError
from unittest.mock import patch
from core.models import *
from datetime import date, timedelta

User = get_user_model()


class TestUserAuthentication(TestCase):
    #normal
    def test_UA_01_login_valid_credentials(self):
        response = self.client.post(reverse('account_login'), {
                                    'login': 'BLSStudent', 'password': 'test123'})
        self.assertEqual(response.status_code, 200)

    #erroneous
    def test_UA_02_login_invalid_credentials(self):
        response = self.client.post(reverse('account_login'), {
                                    'login': 'BLSStudent', 'password': 'jest123'})
        self.assertContains(response, 'error', status_code=200)


class TestBookManagement(TestCase):
    def setUp(self):
        self.client = Client()
        self.book = Book(
            title='BM Test Book',
            author='Author A',
            isbn='9781111111111',
            category=1,
            in_stock=True,
            ebook=True
        )
        self.book.clean()
        self.book.save()
        self.user = User.objects.create_user(
            username='BMUser', password='test123')
        self.user2 = User.objects.create_user(
            username='BMUser2', password='test123')

        self.book2 = Book(
            title='BM Test Book 2',
            author='Author B',
            isbn='9782222222222',
            category=1,
            in_stock=True,
            ebook=True
        )
        self.book2.clean()
        self.book2.save()

    #normal
    def test_BM_07_add_physical_book(self):
        physicalbook = PhysicalBook.objects.create(
            book_id=self.book,
            condition=1,
            with_student=False,
            ready_for_loan=True
        )
        
        self.book.refresh_from_db()
        self.assertEqual(self.book.inventory, 1)
        self.assertEqual(self.book.stock_level, 1)

    #normal
    def test_BM_13_remove_physical_book(self):
        physicalbook = PhysicalBook.objects.create(
            book_id=self.book,
            condition=1,
            with_student=False,
            ready_for_loan=True
        )
        self.assertEqual(self.book.inventory, 1)
        self.assertEqual(self.book.stock_level, 1)

        
        physicalbook.remove()
        self.book.refresh_from_db()  
        self.assertEqual(self.book.inventory, 0)
        self.assertEqual(self.book.stock_level, 0)

    #erroneous
    def test_BM_02_missing(self):
        with self.assertRaises(ValidationError):
            book = Book(
                title='Missing Book',
                author='',
                isbn='9783333333333',
                category=1,
                stock_level=0,
                inventory=0,
                in_stock=False
            )
            book.full_clean()
            book.save()

    #erroneous
    def test_BM_04_invalid_isbn(self):
        with self.assertRaises(ValidationError):
            book = Book(
                title='Invalid ISBN',
                author='Author B',
                isbn='invalidisbn',
                category=1
            )
            book.full_clean()
            book.save()

    #erroneous
    def test_BM_14_spaces(self):
        with self.assertRaises(ValidationError):
            book = Book(
                title='  ',
                author=' ',
                isbn='9784444444444',
                category=1,
                stock_level=0,
                inventory=0,
                in_stock=False
            )
            book.full_clean()
            book.save()

    #erroneous
    def test_BM_03_duplicate_isbn(self):
        with self.assertRaises(ValidationError):
            book = Book(
                title='Duplicate ISBN',
                author='Author D',
                isbn='9781111111111',
                category=1
            )
            book.full_clean()
            book.save()

    # normal - no stock
    def test_BM_08_check_stock_indicator(self):
        pb1 = PhysicalBook.objects.create(
            book_id=self.book2,
            condition=1,
            with_student=False,
            ready_for_loan=True
        )
        pb2 = PhysicalBook.objects.create(
            book_id=self.book2,
            condition=1,
            with_student=False,
            ready_for_loan=True
        )
        self.book.refresh_from_db()
        loan1 = Loan(
            user_id=self.user,
            book_id=self.book2,
            start_date=date.today() - timedelta(days=2),
            end_date=date.today() + timedelta(days=5),
            active=True,
        )
        loan1.save()
        loan2 = Loan(
            user_id=self.user2,
            book_id=self.book2,
            start_date=date.today() - timedelta(days=5),
            end_date=date.today() + timedelta(days=2),
            active=True,
        )
        loan2.save()

        loan1.collect()
        loan2.collect()
        print("Loan 1: BM08", loan1.active, loan1.physicalbook)
        print("Loan 2: BM08", loan2.active, loan2.physicalbook)
        print(
            f"Loan 1: BM08 {LoanIssuanceNotes.objects.get(loan_id=loan1).reason}")
        print(
            f"Loan 2: BM08 {LoanIssuanceNotes.objects.get(loan_id=loan2).reason}")

        self.book2.refresh_from_db()  
        self.assertEqual(self.book2.stock_level, 0)
        self.assertEqual(self.book2.inventory, 2)

    def test_BM_09_default_in_stock_false(self):
        book = Book(
            title='BM In Stock',
            author='Author F',
            isbn='9785555555555',
            category=1
        )
        book.clean()
        book.save()
        self.assertFalse(book.in_stock)
        self.assertEqual(book.stock_level, 0)
        self.assertEqual(book.inventory, 0)

    # boundary ending today
    def test_BM_15_check_stock_indicator(self):
        pb1 = PhysicalBook.objects.create(
            book_id=self.book,
            condition=1,
            with_student=False,
            ready_for_loan=True
        )
        pb2 = PhysicalBook.objects.create(
            book_id=self.book,
            condition=1,
            with_student=False,
            ready_for_loan=True
        )
        print(f'BM15 stock b4 {self.book.stock_level}')
        print(f'BM15 inventory b4 {self.book.inventory}')
        self.book.refresh_from_db()
        loan1 = Loan(
            user_id=self.user,
            book_id=self.book,
            start_date=date.today() - timedelta(days=2),
            end_date=date.today(),
            active=True,
        )
        loan1.save()
        loan2 = Loan(
            user_id=self.user2,
            book_id=self.book,
            start_date=date.today() - timedelta(days=5),
            end_date=date.today(),
            active=True,
        )
        loan2.save()
        loan1.collect()
        loan2.collect()
        print("Loan 1: Bm15", loan1.start_date, loan1.end_date,
              loan1.active, loan1.physicalbook)
        print("Loan 2: Bm15", loan2.start_date, loan2.end_date,
              loan2.active, loan2.physicalbook)
        
        print(f'Bm15 stock aft {self.book.stock_level}')

        self.book.refresh_from_db()
        print(f'Bm15 stock aft rfrs {self.book.stock_level}')


        self.assertEqual(self.book.stock_level, 0)
        self.assertEqual(self.book.inventory, 2)


    # boundary - ending yesterday
    def test_BM_16_check_stock_indicator_dayb4(self):
        pb1 = PhysicalBook.objects.create(
            book_id=self.book,
            condition=1,
            with_student=False,
            ready_for_loan=True
        )
        pb2 = PhysicalBook.objects.create(
            book_id=self.book,
            condition=1,
            with_student=False,
            ready_for_loan=True
        )
        self.book.refresh_from_db()
        loan1 = Loan(
            user_id=self.user,
            book_id=self.book,
            start_date=date.today() - timedelta(days=2),
            end_date=date.today() - timedelta(days=1),
            active=True,
        )
        loan1.save()
        print("Loan 1:", loan1.start_date, loan1.end_date,
              loan1.active, loan1.physicalbook)
        loan2 = Loan(
            user_id=self.user2,
            book_id=self.book,
            start_date=date.today() - timedelta(days=5),
            end_date=date.today() - timedelta(days=1),
            active=True,
        )
        loan2.save()
        loan1.collect()
        loan2.collect()
        print("Loan 2:", loan2.start_date, loan2.end_date,
              loan2.active, loan2.physicalbook)

        self.book.refresh_from_db() 
        self.assertEqual(self.book.stock_level, 2)
        self.assertEqual(self.book.inventory, 2)


class TestLoanManagement(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='LoanUser', password='test123')
        self.book = Book(
            title='Loan Book', author='Author L', isbn='9780000000000', category=1, in_stock=True
        )
        self.book.clean()
        self.book.save()
        self.physicalbook = PhysicalBook.objects.create(
            book_id=self.book, condition=1, with_student=False, ready_for_loan=True
        )

        self.user2 = User.objects.create_user(
            username='LoanUser2', password='test123')
        
    # normal
    def test_LM_01_create_loan_success(self):
        loan = Loan(
            user_id=self.user, book_id=self.book,
            start_date=date.today(), end_date=date.today() + timedelta(days=7), active=True
        )
        loan.save()
        self.assertTrue(loan.active)
        self.assertEqual(LoanIssuanceNotes.objects.get(loan_id=loan).flag, 4)

    #boundary
    def test_LM_02_7days(self):
        loan = Loan(
            user_id=self.user, book_id=self.book,
            start_date=date.today(), end_date=date.today() + timedelta(days=7), active=True
        )
        loan.full_clean()
        loan.save()
        self.assertEqual(LoanIssuanceNotes.objects.get(loan_id=loan).flag, 4)
        self.assertTrue(loan.active)

    #erroneous
    def test_LM_03_reject_loan_if_no_stock(self):
        self.book.stock_level = 0
        self.book.inventory = 0
        self.book.save()
        loan = Loan(
            user_id=self.user, book_id=self.book,
            start_date=date.today(), end_date=date.today() + timedelta(days=7), active=True
        )
        loan.full_clean()
        loan.save()
        self.book.refresh_from_db()
        self.assertEqual(LoanIssuanceNotes.objects.get(loan_id=loan).flag, 1)
        self.assertFalse(loan.active)

    #boundary - reloan within cooldown
    def test_LM_04_block_reloan_within_cooldown(self):
        loan = Loan(
            user_id=self.user, book_id=self.book,
            start_date=date.today() - timedelta(days=7), end_date=date.today() - timedelta(days=3), active=False
        )
        loan.save()

        repeat = Loan(
            user_id=self.user, book_id=self.book,
            start_date=date.today(), end_date=date.today() + timedelta(days=7)
        )
        repeat.full_clean()
        repeat.save()
        self.assertEqual(LoanIssuanceNotes.objects.get(loan_id=repeat).flag, 2)
        self.assertFalse(repeat.active)

    #erroneous
    def test_LM_05_duplicate_active_loan_rejected(self):
        first = Loan(
            user_id=self.user, book_id=self.book,
            start_date=date.today(), end_date=date.today() + timedelta(days=7), active=True
        )
        first.save()

        duplicate = Loan(
            user_id=self.user, book_id=self.book,
            start_date=date.today(), end_date=date.today() + timedelta(days=7), active=True
        )
        duplicate.full_clean()
        duplicate.save()

        self.assertEqual(LoanIssuanceNotes.objects.get(
            loan_id=duplicate).flag, 5)
        self.assertFalse(duplicate.active)

    #normal
    def test_LM_06_allowed_renew(self):
        # no need for physical book here, not collecting loan
        self.book.stock_level = 2
        self.book.inventory = 2
        self.book.save()
        loan1 = Loan(
            user_id=self.user, book_id=self.book,
            start_date=date.today(), end_date=date.today() + timedelta(days=7), active=True, renewed=False
        )
        loan1.save()

        existing_loan = Loan(
            user_id=self.user, book_id=self.book,
            start_date=date.today() - timedelta(5), end_date=date.today(), active=True, renewed=False
        )
        existing_loan.save()
        initial_end = existing_loan.end_date

        existing_loan.renew()
        self.assertEqual(existing_loan.end_date,
                         initial_end + timedelta(days=7))

        loan1.delete()
        self.book.stock_level = 1
        self.book.inventory = 1
        self.book.save()
        existing_loan.delete()

    #boundary
    def test_LM_07_reject_renewal_already(self):
        loan = Loan(
            user_id=self.user, book_id=self.book,
            start_date=date.today(), end_date=date.today() + timedelta(days=7), active=True, renewed=True
        )
        initial_end = loan.end_date
        loan.save()
        issued, flag, reason = loan.extension_eligibility(7)
        self.assertFalse(issued)
        self.assertEqual(flag, 0)

    #erroneous/boundary
    def test_LM_11_reject_loan_too_long(self):
        long_loan = Loan(
            user_id=self.user, book_id=self.book,
            start_date=date.today(), end_date=date.today() + timedelta(days=8), active=True
        )
        long_loan.full_clean()
        long_loan.save()
        self.assertEqual(LoanIssuanceNotes.objects.get(
            loan_id=long_loan).flag, 0)
        self.assertFalse(long_loan.active)

    #normal
    def test_LM_09_return_loan_success(self):
        loan = Loan(
            user_id=self.user, book_id=self.book,
            start_date=date.today(), end_date=date.today() + timedelta(days=7), active=True
        )
        loan.save()
        loan.collect()
        loan.return_book()
        self.assertFalse(loan.active)
        self.assertFalse(loan.custody)
        self.assertTrue(loan.physicalbook.ready_for_loan)
        self.assertFalse(loan.physicalbook.with_student)

    # normal
    def test_LM_10_renewal_rejected_stock(self):
        loan = Loan(
            user_id=self.user, book_id=self.book,
            start_date=date.today(), end_date=date.today() + timedelta(days=7), active=True, renewed=False
        )
        loan.save()
        
        overlapping = Loan(
            user_id=self.user2, book_id=self.book,
            start_date=date.today() + timedelta(7), end_date=date.today() + timedelta(days=10), active=True, renewed=False
        )
        overlapping.save()

        loan.collect()
        original = loan.end_date
        loan.renew()
        self.assertEqual(original, loan.end_date)



class TestOnlineReadingAndReview(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username='Reader', password='test123')
        self.book = Book(
            title='Reading Book1', author='Read Author', isbn='9788888888888', category=1
        )
        self.book2 = Book(
            title='Reading Book2', author='Read Author', isbn='9789999999999', category=1
        )
        self.book.clean()
        self.book.save()
        self.book2.clean()
        self.book2.save()
        self.client.login(username='Reader', password='test123')

    #normal
    def test_OR_02_record_online_reading(self):
        self.client.get(reverse('book', args=[self.book.book_id]))
        self.client.get(reverse('book', args=[self.book2.book_id]))

        record = OnlineBookRead.objects.filter(
            user=self.user, book=self.book.book_id)
        self.assertEqual(record.count(), 1)
        self.assertEqual(record[0].nextbook.book_id, self.book2.book_id)

    #normal
    @patch('core.models.requests.get')
    def test_RS_01_valid_review(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {'has_profanity': False}
        review = Review(book=self.book, comments='cleanwords :)',
                        user_id=self.user)
        check, note = review.checks()
        self.assertTrue(check)
        review.save()

        self.assertTrue(review.see)

    # boundary
    @patch('core.models.requests.get')
    def test_RS_02_block_profanity(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {'has_profanity': True}
        review = Review(book=self.book, comments='badword', user_id=self.user)
        check, note = review.checks()
        self.assertFalse(check)
        review.save()

        self.assertFalse(review.see)

    #erroneous
    def test_RS_03_block_review_email(self):
        review = Review(
            book=self.book, comments='contact me: me@mail.com', user_id=self.user)
        check, note = review.checks()
        self.assertFalse(check)
        review.save()
        self.assertFalse(review.see)

    #erroneous
    def test_RS_04_block_review_phone(self):
        review = Review(
            book=self.book, comments='call me 07700112233', user_id=self.user)
        check, note = review.checks()
        self.assertFalse(check)
        review.save()
        self.assertFalse(review.see)  

    #boundary
    @patch('core.models.requests.get')
    def test_RS_06_fail_api_graceful(self, mock_get):
        mock_get.side_effect = Exception("API down")
        review = Review(book=self.book, comments='This is safe',
                        user_id=self.user)
        check, note = review.checks()
        self.assertFalse(check)
        review.save()
        self.assertFalse(review.see)

    #boundary
    def test_RS_08_block_empty_review(self):
        review = Review(book=self.book, comments='', user_id=self.user)
        check, note = review.checks()
        self.assertFalse(check)
        review.save()
        self.assertFalse(review.see)
    #boundary
    def test_RS_09_block_whitespace_review(self):
        review = Review(book=self.book, comments='   ', user_id=self.user)
        check, note = review.checks()
        self.assertFalse(check)
        review.save()
        self.assertFalse(review.see)
