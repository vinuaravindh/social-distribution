from django.contrib import admin
from .models import Author, Like, Comment, Post

# Register your models here.
admin.site.register(Author)
admin.site.register(Like)
admin.site.register(Comment)
admin.site.register(Post)