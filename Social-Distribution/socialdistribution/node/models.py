from email._header_value_parser import ContentType
from django.db import models
from django.contrib.auth.hashers import make_password, check_password
from encrypted_model_fields.fields import EncryptedCharField
from django.core.validators import URLValidator
import django
import datetime

class Author(models.Model):
    id = models.AutoField(primary_key=True)
    display_name = models.CharField(max_length=50, blank=False, null=False)
    description = models.CharField(max_length=150, default="", blank=True, null=True)
    host = models.CharField(max_length=50, blank=True, null=True) # URL of host node
    github = models.CharField(max_length=50, blank=True, null=True) # URL of author's Github
    profile_image = models.ImageField(upload_to='images/profilePictures', default="null", blank=True, null=True)
    page = models.CharField(max_length=100, blank=True, null=True) # URL of user's HTML profile page
    friends = models.ManyToManyField('Author', blank=True)
    password = models.CharField(max_length=128)
    email = models.EmailField(max_length=50, default='example@example.com', unique=True)
    is_active = models.BooleanField(default=True)
    is_admin = models.BooleanField(default=False)
    is_staff = models.BooleanField(default=False)  # Required for admin interface

    def __str__(self):
        return self.display_name
    
    def save(self, *args, **kwargs):
        # Hash the password if it's not already hashed
        if not self.pk or Author.objects.get(pk=self.pk).password != self.password:
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def check_password_custom(self, raw_password):
        return check_password(raw_password, self.password)
    
class RemoteNode(models.Model):
    name = models.CharField(max_length=100, unique=True, help_text="Friendly name for the remote node")
    url = models.URLField(max_length=200, validators=[URLValidator()], help_text="URL of the remote node")
    username = models.CharField(max_length=150, help_text="Username for authentication")
    password = EncryptedCharField(max_length=128, help_text="Password for authentication")  # Encrypted field
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    is_active = models.BooleanField(default=True)

    def __str__(self):
        return self.name

    def save(self, *args, **kwargs):
        # Hash the password if it's not already hashed
        if not self.pk or RemoteNode.objects.get(pk=self.pk).password != self.password:
            self.password = make_password(self.password)
        super().save(*args, **kwargs)

    def check_password_custom(self, raw_password):
        return check_password(raw_password, self.password)
    

class Like(models.Model):
    object_id = models.AutoField(primary_key=True)
    created_at = models.DateTimeField(default=django.utils.timezone.now, db_index=True)
    liker = models.ForeignKey(Author, on_delete=models.CASCADE, null=True)

    class Meta:
        abstract = True


class Post(models.Model):
    VISIBILITY_CHOICES = [
        ('PUBLIC', 'Public'),
        ('FRIENDS', 'Friends'),
        ('UNLISTED', 'Unlisted'),
        ('DELETED', 'Deleted'),
    ]

    id = models.AutoField(primary_key=True)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, null=True)
    title = models.CharField(max_length=100)
    description = models.TextField()  # Posts need a short description
    contentType = models.TextField()
    text_content = models.TextField(blank=True)  # Text post content (optional)
    image_content = models.TextField(blank=True)  # Link to image
    published = models.DateTimeField()
    visibility = models.CharField(
        max_length=50,
        choices=VISIBILITY_CHOICES,
        default='PUBLIC',
    )


class Repost(models.Model):
    id = models.AutoField(primary_key=True)
    original_post = models.ForeignKey(Post, on_delete=models.CASCADE, null=True)
    shared_by = models.ForeignKey(Author, on_delete=models.SET_NULL, null=True)
    shared_date = models.DateTimeField(auto_now_add=True)

class Comment(models.Model):
    id = models.AutoField(primary_key=True)
    post = models.ForeignKey(Post, on_delete=models.CASCADE)
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    published = models.DateTimeField(auto_now_add=True, null=True, db_index=True)
    text = models.TextField()

class PostLike(Like):
    owner = models.ForeignKey(Post, on_delete=models.CASCADE)

class CommentLike(Like):
    owner = models.ForeignKey(Comment, on_delete=models.CASCADE)
    
class Image(models.Model):
    author = models.ForeignKey(Author, on_delete=models.CASCADE)
    image = models.ImageField(upload_to='images/')
    uploaded_at = models.DateTimeField(auto_now_add=True, db_index=True)

class Follow(models.Model):
    follower = models.CharField(max_length=200)  # Full URL of the follower author
    following = models.CharField(max_length=200)  # Full URL of the author being followed
    approved = models.BooleanField(default=False, db_index=True)  # To track if the follow request is approved
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('follower', 'following')  # Prevent duplicate follow entries

    def is_friend(self):
        # Check if the following author follows back the follower
        return Follow.objects.filter(follower=self.following, following=self.follower, approved=True).exists()
