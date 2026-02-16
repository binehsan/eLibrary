from django.contrib import admin

# Register your models here.
from django.contrib import admin
from django.contrib.auth.admin import UserAdmin as BaseUserAdmin
from django.contrib.auth.models import Group
from .models import *
from .forms import *  # Replace with your actual user model
from django.core.exceptions import PermissionDenied
from django.db import transaction


class CustomUserAdmin(BaseUserAdmin):
    list_display = ('email', 'username', 'first_name', 'last_name', 'is_staff')
    list_filter = ('is_staff', 'is_superuser', 'is_active', 'groups')
    search_fields = ('email', 'username', 'first_name', 'last_name')
    ordering = ('email',)

    fieldsets = (
        (None, {'fields': ('email', 'password')}),
        ('Personal info', {'fields': ('first_name', 'last_name', 'username')}),
        ('Permissions', {'fields': ('is_active', 'is_staff',
         'is_superuser', 'groups', 'user_permissions', 'banned')}),
        ('Important dates', {'fields': ('last_login', 'date_joined')}),
    )
    add_fieldsets = (
        (None, {
            'classes': ('wide',),
            'fields': ('email', 'username', 'password1', 'password2', 'is_staff', 'is_active', 'groups')}
         ),
    )

    def save_model(self, request, obj, form, change):
        allowed_super = True if request.user.is_superuser else False
        if obj.username == 'blssuper':
            self.message_user(
                request, 'You cannot alter the superuser account.')
            return  

        if obj.is_superuser and not allowed_super:
            self.message_user(
                request, 'You do not have permission to create a superuser. User saved without this attribute.')
            obj.is_superuser = False

        if obj.is_staff and not allowed_super:
            self.message_user(
                request, 'You do not have permission to create a staff user. User saved without this attribute.')
            obj.is_staff = False

        super().save_model(request, obj, form, change)

        def verify_valid(self, request, obj):
            if obj.username == 'blssuper':
                self.message_user(request, 'You cannot alter the superuser.')
            else:
                print(obj.groups.all())
                if obj.groups.filter(name='Admins').exists() and not allowed_super:
                    self.message_user(
                        request, 'You do not have permission to create an admin user. This user has been saved as a student.')
                    obj.groups.remove(Group.objects.get(name='Admins'))
                    obj.groups.add(Group.objects.get(name='Students'))

        super().save_model(request, obj, form, change)
        transaction.on_commit(lambda: verify_valid(self, request, obj))


class LoanIssuanceNotesAdmin(admin.ModelAdmin):
    list_display = ['physicalbook', 'user_id', 'reason', 'success']


class PhysicalBookAdmin(admin.ModelAdmin):
    list_display = ['physical_id', 'book_id',
                    'condition', 'withstudent', 'readyforloan']


class BookAdmin(admin.ModelAdmin):
    # form = BookAdminForm
    # add_fieldsets = (
    #     ('📚 Instructions', {
    #         'fields': (),
    #         'description': 'Please fill out the form below to add a new book to the library.'
    #     }),
    #     ('Book Uplink', {'fields': ('title', 'author', 'isbn', 'category', 'file', 'description')}),
    # )

    fieldsets = (
        ('Book Data', {'fields': ('title', 'author', 'isbn', 'category',
         'file', 'description', 'audio_version', 'audio', 'text', 'ebook')}),
    )

    actions = ['Proper_Delete']
    list_display = ['book_id', 'title', 'author',
                    'stock_level', 'inventory', 'in_stock', 'category']
    # removed stock_level and inventory to prevent staff manipulation

    def Proper_Delete(self, request, queryset):
        for book in queryset:
            book.delete()
        self.message_user(request, 'Deleted Successfully.')


class PhysicalBookAdmin(admin.ModelAdmin):
    actions = ['Proper_Delete', 'Mark_Damaged']
    list_display = ['physical_id', 'book_id',
                    'ready_for_loan', 'with_student', 'condition']

    def Proper_Delete(self, request, queryset):
        for book in queryset:
            book.remove()
        self.message_user(request, 'Deleted Successfuly.')

    def Mark_Damaged(self, request, queryset):
        for book in queryset:
            if book.with_student == True:
                self.message_user(
                    request, 'Selected book is still with a student.')
            else:
                book.damage()
                self.message_user(request, 'Marked as Damaged.')


class LoanAdmin(admin.ModelAdmin):
    actions = ['renew', 'collect', 'return_book', 'proper_delete']
    list_display = ['physicalbook', 'user_id', 'custody',
                    'rejected', 'renewed', 'start_date', 'end_date']

    def save_model(self, request, obj, form, change):
        obj.save(request=request)

    def renew(self, request, queryset):
        for loan in queryset:
            if loan.renewed == False:
                loan.renew()
                self.message_user(
                    request, 'Selected loans have been renewed for 7days ')
            else:
                self.message_user(
                    request, 'Selected loans have already been renewed')

    def collect(self, request, queryset):
        for loan in queryset:
            if loan.start_date <= datetime.today().date():
                if loan.custody == False:
                    loan.collect()
                    self.message_user(
                        request, f'Selected loans marked as collected')
                else:
                    self.message_user(
                        request, 'Selected loaned book is already in custody')
            else:
                self.message_user(request, 'Selected loan has not begun yet')

    def return_book(self, request, queryset):
        for loan in queryset:
            if loan.custody == True:
                loan.return_book()
                self.message_user(request, 'Selected loans have been returned')
            else:
                self.message_user(
                    request, 'Selected loans have already been returned')

    def proper_delete(self, request, queryset):
        for loan in queryset:
            loan.delete()
        self.message_user(request, 'Deleted Successfully.')


class LoanIssuanceNotesAdmin(admin.ModelAdmin):
    list_display = ['physicalbook', 'book', 'user_id', 'issued', 'loan_id']


class DamageAdmin(admin.ModelAdmin):
    list_display = ['physicalbook', 'user_id', 'category', 'resolved']
    fieldsets = (
        ('Damage Data', {'fields': ('loan_id', 'student_comments', 'liabile',
         'penalty_issued', 'date', 'resolved', 'category', 'admin_comments')}),
    )

    def Mark_Resolved(self, request, queryset):
        for damage in queryset:
            damage.resolved = True
            damage.save()

    def Confirm_Liability(self, request, queryset):
        for damage in queryset:
            damage.liabile = True
            damage.save()

    actions = ['Mark_Resolved', 'Confirm_Liability']


class ReviewAdmin(admin.ModelAdmin):
    list_display = ['user_id', 'book', 'see']

    def hide_review(self, request, queryset):
        for review in queryset:
            review.see = False
            review.save()

    actions = ['hide_review']


class ReviewNoteAdmin(admin.ModelAdmin):
    list_display = ['note_id', 'user_id', 'blocked']


class PenaltyAdmin(admin.ModelAdmin):
    list_display = ['penalty_id', 'user_id', 'paid', 'physicalbook']
    fieldsets = (
        ('Penalty Data', {'fields': ('damage_id', 'issuance_date', 'paid',
         'pay_method', 'amount', 'admin_comments', 'loan_id', 'reason_overdue')}),
    )

    def Mark_Paid(self, request, queryset):
        for penalty in queryset:
            penalty.paid = True
            penalty.save()

    actions = ['Mark_Paid']


admin.site.register(BLSUser, CustomUserAdmin)
admin.site.unregister(Group)
admin.site.register(Group)
admin.site.register(LoanIssuanceNotes, LoanIssuanceNotesAdmin)

admin.site.register(Book, BookAdmin)
admin.site.register(Loan, LoanAdmin)
admin.site.register(Damage, DamageAdmin)
admin.site.register(Review, ReviewAdmin)
admin.site.register(Penalty, PenaltyAdmin)
admin.site.register(ReviewNote, ReviewNoteAdmin)
admin.site.register(PhysicalBook, PhysicalBookAdmin)
admin.site.register(OnlineBookRead)

# onlinebookread, bookmark
