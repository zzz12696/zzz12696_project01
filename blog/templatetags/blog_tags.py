from django import template

from blog.models import Entry, Category, Tag


register = template.Library()  # django 1.9之后才有的


@register.simple_tag
def get_recent_entries(num=5):
    return Entry.objects.all().order_by('-created_time')[:num]


@register.simple_tag
def get_popular_entries(num=5):
    return Entry.objects.all().order_by('-visiting')[:num]


@register.simple_tag
def get_category():
    return Category.objects.all()


@register.simple_tag
def get_entry_count_of_category(category_id):
    return Entry.objects.filter(category=category_id).count()


@register.simple_tag
def archives():
    '''
    dates：Django ORM给我们提供的方法，返回一个列表
    order='DESC'：逆序排序
    :return: 返回一个列表
    '''
    return Entry.objects.dates('created_time', 'month', order='DESC')


@register.simple_tag
def get_entry_count_of_date(year, month):
    return Entry.objects.filter(created_time__year=year, created_time__month=month).count()


@register.simple_tag
def get_tags():
    return Tag.objects.all()
