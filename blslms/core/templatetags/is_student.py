from django import template

register = template.Library()

@register.filter(name='is_student')
def is_student(user):
    return user.groups.filter(name="Students").exists()
