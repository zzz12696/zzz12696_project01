from django.shortcuts import render, redirect, get_object_or_404
from django.db.models import Q
from django.conf import settings
from django_comments.models import Comment

import markdown
import pygments
import requests
import json

from . import models
from utils.mypage import Page


def index(request):
    entries = models.Entry.objects.all()

    if entries:
        entries_count = entries.count()
        page_num = request.GET.get('page', 1)
        url_prefix = "/blog/?"
        page_obj = Page(page_num=page_num, total_count=entries_count, per_page=5, url_prefix=url_prefix, max_page=5)
        entries = entries[page_obj.start:page_obj.end]
        page_html = page_obj.page_html()
        return render(request, 'blog/index.html', locals())

    else:
        error_msg = '暂无文章'
        return render(request, 'blog/index.html', {
            'error_msg': error_msg,
        })


def detail(request, blog_id):
    entry = get_object_or_404(models.Entry, id=blog_id)
    entry.increase_visting()

    md = markdown.Markdown(extensions=[
        'markdown.extensions.extra',
        'markdown.extensions.codehilite',
        'markdown.extensions.toc',
    ])
    entry.body = md.convert(entry.body)
    entry.toc = md.toc

    comment_list = list()

    def get_comment_list(comments):
        for comment in comments:
            comment_list.append(comment)
            children = comment.child_comment.all()
            if len(children) > 0:
                get_comment_list(children)

    top_comments = Comment.objects.filter(object_pk=blog_id, parent_comment=None, content_type__app_label='blog').order_by('-submit_date')
    get_comment_list(top_comments)

    return render(request, 'blog/detail.html', locals())


def category(request, category_id):
    c = get_object_or_404(models.Category, id=category_id)
    entries = models.Entry.objects.filter(category=c)

    if entries:
        entries_count = entries.count()
        page = request.GET.get('page', 1)
        url_prefix = "/blog/category/{}/?".format(category_id)
        page_obj = Page(page_num=page, total_count=entries_count, per_page=5, url_prefix=url_prefix, max_page=5)
        entries = entries[page_obj.start:page_obj.end]
        page_html = page_obj.page_html()

        return render(request, 'blog/index.html', locals())

    else:
        error_msg = '该分类下暂无文章'
        return render(request, 'blog/index.html', {
            'error_msg': error_msg,
        })


def tag(request, tag_id):
    tag = get_object_or_404(models.Tag, id=tag_id)
    entries = models.Entry.objects.filter(tags=tag)

    if entries:
        entries_count = entries.count()
        page = request.GET.get('page', 1)
        url_prefix = "/blog/tag/{}/?".format(tag_id)
        page_obj = Page(page_num=page, total_count=entries_count, per_page=5, url_prefix=url_prefix, max_page=5)
        entries = entries[page_obj.start:page_obj.end]
        page_html = page_obj.page_html()

        return render(request, 'blog/index.html', locals())

    else:
        error_msg = '此标签下暂无文章'
        return render(request, 'blog/index.html', {
            'error_msg': error_msg,
        })


def search(request):
    keyword = request.GET.get('keyword', None)
    if not keyword:
        return redirect('/blog/')

    entries = models.Entry.objects.filter(Q(title__icontains=keyword)
                                          | Q(body__icontains=keyword)
                                          | Q(abstract__icontains=keyword))

    if entries:
        total_count = entries.count()
        page_num = request.GET.get('page', 1)
        url_prefix = "/blog/search/?keyword={}".format(keyword)
        page_obj = Page(page_num=page_num, total_count=total_count, per_page=5, url_prefix=url_prefix, max_page=5)
        entries = entries[page_obj.start:page_obj.end]
        page_html = page_obj.page_html()

        return render(request, 'blog/index.html', locals())

    else:
        error_msg = '没有与此关键词匹配的文章'
        return render(request, 'blog/index.html', {
            'error_msg': error_msg,
        })


def archives(request, year, month):
    entries = models.Entry.objects.filter(created_time__year=year, created_time__month=month)

    if entries:
        entries_count = entries.count()
        page = request.GET.get('page', 1)
        url_prefix = "/blog/archives/{0}/{1}/?".format(year, month)
        page_obj = Page(page_num=page, total_count=entries_count, per_page=5, url_prefix=url_prefix, max_page=5)
        entries = entries[page_obj.start:page_obj.end]
        page_html = page_obj.page_html()

        return render(request, 'blog/index.html', locals())

    else:
        return render(request, 'blog/404.html', locals())


def permission_denied(request):
    return render(request, 'blog/403.html', locals())


def page_not_found(request):
    return render(request, 'blog/404.html', locals())


def page_error(request):
    return render(request, 'blog/500.html', locals())


def login(request):
    code = request.GET.get('code', None)
    if code is None:
        return redirect('/blog/')

    access_token_url = 'https://api.weibo.com/oauth2/access_token?client_id={0}&client_secret={1}&grant_type=authorization_code&redirect_uri=http://www.muzicm.cn/login?&code={2}'.format(settings.CLIENT_ID, settings.APP_SECRET, code)
    ret = requests.post(access_token_url)
    data = ret.text
    data_dict = json.loads(data)
    token = data_dict['access_token']
    uid = data_dict['uid']

    request.session['token'] = token
    request.session['uid'] = uid
    request.session['login'] = True

    user_info_url = 'https://api.weibo.com/2/users/show.json?access_token={0}&uid={1}'.format(token, uid)
    user_info = requests.get(user_info_url)

    user_info_dict = json.loads(user_info.text)
    request.session['screen_name'] = user_info_dict['screen_name']
    request.session['profile_image_url'] = user_info_dict['profile_image_url']

    return redirect(request.GET.get('next', '/blog/'))


def logout(request):
    if request.session['login']:
        del request.session['login']
        del request.session['uid']
        del request.session['token']
        del request.session['screen_name']
        del request.session['profile_image_url']

        return redirect(request.GET.get('next', '/blog/'))
    else:
        return redirect('/blog/')


def reply(request, comment_id):
    if not request.session.get('login', None) and not request.user.is_authenticated():
        return redirect('/')
    parent_comment = get_object_or_404(Comment, id=comment_id)
    return render(request, 'blog/reply.html', locals())


def about_me(request):
    return render(request, 'blog/about_me.html')


def call_me(request):
    return render(request, 'blog/call_me.html')
