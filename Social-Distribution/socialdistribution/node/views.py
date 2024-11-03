from django.core import signing
from django.http import HttpResponse, HttpResponseRedirect, HttpResponseForbidden
from django.utils import timezone
from django.core.paginator import Paginator
from django.shortcuts import render, get_object_or_404, redirect
from django.urls import reverse
from django.views.generic import ListView
from .models import Post, Author, PostLike, Comment, Like, Follow, Repost, CommentLike
from django.contrib import messages
from django.db.models import Q, Count, Exists, OuterRef, Subquery
import datetime
import os
from .forms import AuthorProfileForm
from django.core.paginator import Paginator
from .forms import ImageUploadForm
import http.client
import json
from rest_framework.permissions import IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from django.contrib.auth.decorators import login_required

from .utils import get_authenticated_user_id, AuthenticationFailed
from rest_framework.response import Response
from rest_framework import status

class AuthorListView(ListView):
    model = Author
    template_name = 'authors.html'  # Specify the template to use
    context_object_name = 'authors'  # Name of the context object to access in the template

    # Get the query of the GET request
    def get_queryset(self):
        # Get the base queryset (all authors)
        queryset = Author.objects.all()

        # Get the search query and field
        query = self.request.GET.get('q')
        field = self.request.GET.get('field')

        # If no query is provided, return all authors
        if not query:
            return queryset

        # Perform filtering based on the field provided
        if field:
            # If a specific field is provided, filter by that field
            if field == "display_name":
                queryset = queryset.filter(display_name__icontains=query)
            elif field == "host":
                queryset = queryset.filter(host__icontains=query)
            elif field == "github":
                queryset = queryset.filter(github__icontains=query)
            elif field == "profile_image":
                queryset = queryset.filter(profile_image__icontains=query)
            elif field == "page":
                queryset = queryset.filter(page__icontains=query)
            else:
                # Return an empty queryset if the field is invalid
                queryset = Author.objects.none()
        else:
            # If no specific field is provided, search across all relevant fields
            queryset = queryset.filter(
                Q(display_name__icontains=query) |
                Q(host__icontains=query) |
                Q(github__icontains=query) |
                Q(profile_image__icontains=query) |
                Q(page__icontains=query)
            )

        return queryset


def editor(request):
    """
    Open menu to edit contents for a post request
    """
    return render(request, "editor.html")

def edit_post(request, post_id):
    author = get_author(request)
    post = get_object_or_404(Post, id=post_id)

    if author is None:
        return HttpResponseForbidden("You must be logged in to edit posts.")

    if post.author != author:
        return HttpResponseForbidden("You are not allowed to edit this post.")

    if request.method == 'POST':

        title = request.POST.get('title')
        text_content = request.POST.get('body-text')
        visibility = request.POST.get('visibility')

        if not title or not text_content:
            messages.error(request, "Title and description cannot be empty.")
            return render(request, 'edit_post.html', {
                'post': post,
                'author_id': author.id,
            })

        post.title = title
        post.text_content = text_content
        post.visibility = visibility
        post.published = datetime.datetime.now()
        post.save()

        return redirect('view_post', post_id=post.id)

    else:
        return render(request, 'edit_post.html', {
            'post': post,
            'author_id': author.id,
        })


def save(request):
    """
    Create a new post!
    """
    author = get_author(request)
    print(request.POST)
    content_type = request.POST["contentType"]
    if content_type != "image":
        post = Post(title=request.POST["title"],
                    description=request.POST["description"],
                    text_content=request.POST["content"],
                    content_type=content_type,
                    visibility=request.POST["visibility"],
                    published=timezone.make_aware(datetime.datetime.now(), datetime.timezone.utc),
                    author=author,
        )
        post.save()
    else:
        image = request.FILES["image"]
        file_suffix = os.path.splitext(image.name)[1]
        content_type = request.POST["contentType"]
        content_type += '/' + file_suffix
        post = Post(title=request.POST["title"],
                    description=request.POST["description"],
                    image_content=request.POST["content"],
                    content_type=content_type,
                    visibility=request.POST["visibility"],
                    published=timezone.make_aware(datetime.datetime.now(), datetime.timezone.utc),
                    author=author,
                    )
        post.save()
    return(redirect('/node/'))

def delete_post(request, post_id):
    author = get_author(request)
    post = get_object_or_404(Post, id=post_id)

    if post.author != author:
        return HttpResponseForbidden("You are not allowed to delete this post.")

    if request.method == 'POST':
        # Set the visibility to 'DELETED'
        post.visibility = 'DELETED'
        post.save()
        messages.success(request, "Post has been deleted.")
        return redirect('index')


def post_like(request, id):
    """
    Method for liking a post given an ID
    If already liked by requesting author, unlike
    """
    author = get_author(request)
    post = get_object_or_404(Post, pk=id)
    if PostLike.objects.filter(owner=post, liker=author).exists():
        PostLike.objects.filter(owner=post, liker=author).delete()
    else:
        new_like = PostLike(owner=post, liker=author)
        new_like.save()
    return(redirect(f'/node/posts/{id}/'))

def comment_like(request, id):
    """
    Method for liking a comment given comment ID
    if already liked by requesting author, removes the like
    """
    author = get_author(request)
    comment = get_object_or_404(Comment, pk=id)
    post = get_object_or_404(Post, pk=comment.post.id)
    if CommentLike.objects.filter(owner=comment, liker=author).exists():
        CommentLike.objects.filter(owner=comment, liker=author).delete()
    else:
        new_like = CommentLike(owner=comment, liker=author)
        new_like.save()
    return(redirect(f'/node/posts/{post.id}/'))

def add_comment(request, id):
    """
    Add a comment to a question
    Get question from ID, fill out model details with request,
    save model, go to results page
    """
    if request.method != "POST":
        return HttpResponse(status=400)
    post = get_object_or_404(Post, pk=id)

    # Get request contents
    author = get_author(request)
    text = request.POST["content"]


    new_comment = Comment(post=post, text=text, author=author)
    new_comment.save()
    # Return to question
    return(redirect(f'/node/posts/{id}/'))


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def view_post(request, post_id):
    """
    For viewing a post
    Returns 403 for visibility conflicts
    Otherwise, render the post
    """

    post = get_object_or_404(Post, id=post_id)
    author = get_author(request)
    liked = False

    if post.author != author: # if user that is not the creator is attempting to view
        if post.visibility == "FRIENDS":
            try:
                follow = get_object_or_404(Follow, follower=author, following = post.author)
            except:
                return HttpResponse(status=403)
            if follow.is_friend():
                return HttpResponse(status=403)

    if post.visibility == "PRIVATE":
        if post.author != author:
            return HttpResponse(status=403)

    if PostLike.objects.filter(owner=post, liker=author).exists():
        liked = True

    # user_likes strategy obtained from Microsoft Copilot, Oct. 2024
    # Find likes from current user matching the queried comment
    user_likes = CommentLike.objects.filter(owner=OuterRef('pk'), liker=author)

    return render(request, "post.html", {
        "post": post,
        "id": post_id,
        'likes': PostLike.objects.filter(owner=post),
        'author': author,
        'liked' : liked,
        'author_id': author.id,
        'comments': Comment.objects.filter(post=post)
                  .annotate(likes=Count('commentlike'),
                            liked=Exists(user_likes)
                            ),
    })

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def profile(request, author_id):
    user = get_object_or_404(Author, id=author_id)
    current_author = get_author(request) # logged in author
    ownProfile = (user == current_author)

    is_following = Follow.objects.filter( # if logged in author following the user
        follower="http://darkgoldenrod/api/authors/" + str(current_author.id),
        following="http://darkgoldenrod/api/authors/" + str(author_id),
        approved=True,
    ).exists()
    if is_following:
        is_followback = Follow.objects.filter(  # ... see if user is following back
            follower="http://darkgoldenrod/api/authors/" + str(author_id),
            following="http://darkgoldenrod/api/authors/" + str(current_author.id),
            approved=True,
        ).exists()
        is_pending = False
    else:
        is_followback = False
        is_pending = Follow.objects.filter( # if logged in author following the user
            follower="http://darkgoldenrod/api/authors/" + str(current_author.id),
            following="http://darkgoldenrod/api/authors/" + str(author_id),
            approved=False,
        ).exists()

    visible_tags = ['PUBLIC']
    if is_followback or user==current_author: # if logged in user is friends with user or if logged in user viewing own profile
        visible_tags.append('FRIENDS') # show friend visibility posts
        if user==current_author: # if logged in user viewing own profile, show unlisted posts too
            visible_tags.append('UNLISTED')
    authors_posts = Post.objects.filter(author=user, visibility__in= visible_tags).exclude(description="Public Github Activity").order_by('-published') # most recent on top
    retrieve_github(user)
    github_posts = Post.objects.filter(author=user, visibility__in=visible_tags, description="Public Github Activity").order_by('-published')

    return render(request, "profile/profile.html", {
        'user': user,
        'posts': authors_posts,
        'ownProfile': ownProfile,
        'is_following': is_following,
        'is_pending': is_pending,
        'activity': github_posts,
    })

def retrieve_github(user):
    # 10/19/2024
    # Me: How to retrieve public github activity of a user, based on their username, to display in an html
    # OpenAI ChatGPT 40 mini generated:
    # Starts here
    conn = http.client.HTTPSConnection("api.github.com")
    headers = {
        'User-Agent': 'node'
    }
    conn.request("GET", f"/users/{user.github}/events/public", headers=headers)
    res = conn.getresponse()
    data = res.read()
    activity = json.loads(data.decode("utf-8")) if res.status == 200 else []
    # Ends here

    # 10/28/2024
    # Me: Retrieve the different event types, the repo, the date in each event in the json and create them into post if they do not yet exist in the database
    # OpenAI ChatGPT 40 mini generated:
    # Starts here
    for event in activity:
        # Extract the event type and creation date
        event_type = event.get("type")
        created_at = event.get("created_at")

        # Create a better description based on the event type
        if event_type == "PushEvent":
            post_description = f"Pushed {len(event.get('payload', {}).get('commits', []))} commit(s) to {event['repo']['name']}."
        elif event_type == "ForkEvent":
            post_description = f"Forked the repository {event['repo']['name']}."
        elif event_type == "CreateEvent":
            post_description = f"Created a new {event['payload'].get('ref_type')} '{event['payload'].get('ref')}' in {event['repo']['name']}."
        elif event_type == "PullRequestEvent":
            post_description = f"Opened a pull request '{event['payload']['pull_request']['title']}' in {event['repo']['name']}."
        elif event_type == "IssuesEvent":
            post_description = f"Created an issue '{event['payload']['issue']['title']}' in {event['repo']['name']}."
        else:
            post_description = f"Performed a {event_type.lower()} action in {event['repo']['name']}."

        # Convert created_at string to a datetime object
        naive_published_date = datetime.datetime.strptime(created_at, "%Y-%m-%dT%H:%M:%SZ")
        published_date = timezone.make_aware(naive_published_date, datetime.timezone.utc)

        # Check for existing post and create new post if it doesn't exist
        if not Post.objects.filter(author=user, title=event_type, text_content=post_description,
                                   published=published_date).exists():
            Post.objects.create(
                author=user,
                title=event_type,
                description="Public Github Activity",
                visibility='PUBLIC',
                published=published_date,  # Set the published date from the activity
                text_content=post_description,
            )
    # Ends here

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def edit_profile(request, author_id):
    user = get_object_or_404(Author, id=author_id)

    original_github = user.github

    if request.method == 'POST':
        form = AuthorProfileForm(request.POST, request.FILES, instance=user)
        if form.is_valid():
            # Delete old GitHub activity posts when new GitHub user inputted
            if original_github != user.github:
                Post.objects.filter(author=user, text_content="Public Github Activity").delete()

            form.save()  # Save the form data
            return redirect('profile', author_id=user.id)  # Redirect to the profile view after saving
    else:
        form = AuthorProfileForm(instance=user)

    return render(request, 'profile/edit_profile.html', {'form': form, 'user': user})

def followers_following(request, author_id):
    profileUserUrl = "http://darkgoldenrod/api/authors/" + str(author_id)  # user of the profile

    # find a diff way to do this tbh
    see_follower = request.GET.get('see_follower', 'true') == 'true'

    if see_follower:
        # Get all followers by checking the Follow model
        users = Follow.objects.filter(following=profileUserUrl, approved=True).values_list('follower', flat=True)
        title = "Followers"
    else:
        users = Follow.objects.filter(follower=profileUserUrl, approved=True).values_list('following', flat=True)
        title = "Followings"

    user_ids = [url.replace("http://darkgoldenrod/api/authors/", "") for url in users]
    user_authors = Author.objects.filter(id__in=user_ids)

    return render(request, 'follower_following.html', {
        'authors': user_authors,
        'DisplayTitle': title})

def get_author(request):
    """
    Retrieves the authenticated Author instance.
    Returns:
        Author instance if authenticated, else None.
    """
    if request.user.is_authenticated:
        return request.user  # Assumes request.user is an Author instance
    return None

# With help from Chat-GPT 4o, OpenAI, 2024-10-14
def follow_author(request, author_id):
    # Get the author being followed
    author_to_follow = get_object_or_404(Author, id=author_id).id

    # Get the logged-in author (assuming you have a user to author mapping)
    current_author = get_author(request).id # Adjust this line to match your user-author mapping

    # Check if the follow relationship already exists
    follow_exists = Follow.objects.filter(follower="http://darkgoldenrod/api/authors/" + str(current_author), following="http://darkgoldenrod/api/authors/" + str(author_to_follow)).exists()

    if not follow_exists:
        # Create a new follow relationship
        Follow.objects.create(follower="http://darkgoldenrod/api/authors/" + str(current_author), following="http://darkgoldenrod/api/authors/" + str(author_to_follow))
        messages.success(request, "You sucessfully followed this author.")
    else:
        print("No follow relationship exists between these authors.")
        messages.warning(request, "You already followed this author.")

    # Redirect back to the authors list or a success page
    return redirect('authors')

# With help from Chat-GPT 4o, OpenAI, 2024-10-14
def unfollow_author(request, author_id):
    # Get the author being followed
    author_to_unfollow = get_object_or_404(Author, id=author_id).id

    # Get the logged-in author (assuming you have a user to author mapping)
    current_author = get_author(request).id # Adjust this line to match your user-author mapping

    # Check if the follow relationship already exists
    follow_exists = Follow.objects.filter(follower="http://darkgoldenrod/api/authors/" + str(current_author), following="http://darkgoldenrod/api/authors/" + str(author_to_unfollow)).exists()

    if follow_exists:
        # Create a new follow relationship
        follow = get_object_or_404(Follow, follower="http://darkgoldenrod/api/authors/" + str(current_author), following="http://darkgoldenrod/api/authors/" + str(author_to_unfollow))
        # Delete the Follow object to unfollow the author
        follow.delete()
        messages.success(request, "You have successfully unfollowed this author.")

    if not follow_exists:
        # Create a new follow relationship
        print("No follow relationship exists between these authors.")
        messages.warning(request, "You are not following this author.")

    # Redirect back to the authors list or a success page
    return redirect('authors')

def follow_requests(request, author_id):
    current_author = get_author(request)  # logged in author
    current_follow_requests = Follow.objects.filter(following="http://darkgoldenrod/api/authors/" + str(current_author.id), approved=False)

    follower_authors = []
    for a_request in current_follow_requests:
        follower_id = a_request.follower.replace("http://darkgoldenrod/api/authors/", "")
        follower_author = get_object_or_404(Author, id=follower_id)
        follower_authors.append(follower_author)

    print(f"Content of follow_authors: {follower_authors}")
    return render(request, 'follow_requests.html', {
        'follow_authors': follower_authors,
        'author_id': author_id,
    })

def approve_follow(request, author_id, follower_id):
    follow_request = get_object_or_404(Follow, follower="http://darkgoldenrod/api/authors/" + str(follower_id), following = "http://darkgoldenrod/api/authors/" + str(author_id))
    follow_request.approved = True
    follow_request.save()
    return redirect('follow_requests', author_id=author_id)  # Redirect to the profile view after saving

def decline_follow(request, author_id, follower_id):
    follow_request = get_object_or_404(Follow, follower="http://darkgoldenrod/api/authors/" + str(follower_id), following = "http://darkgoldenrod/api/authors/" + str(author_id))
    follow_request.delete()
    return redirect('follow_requests', author_id=author_id)  # Redirect to the profile view after saving

# With help from Chat-GPT 4o, OpenAI, 2024-10-14
### WARNING: Only works for posts from authors of the same node right now
# Shows posts from followings and friends
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def display_feed(request):
    """
    Display posts from the authors the logged-in user is following.
    """
    # Get the current user's full author URL
    current_author = get_author(request).id

    # Get filter option from URL query parameters (default is 'all')
    filter_option = request.GET.get('filter', 'all')

    public_posts = Post.objects.filter(visibility="PUBLIC")

    # Get the authors that the current user is following
    follow_objects = Follow.objects.filter(follower="http://darkgoldenrod/api/authors/" + str(current_author), approved=True)

    followings = list(follow_objects.values_list('following', flat=True))
    cleaned_followings = [int(url.replace('http://darkgoldenrod/api/authors/', '')) for url in followings]


    friends = [follow.following for follow in follow_objects if follow.is_friend()]
    cleaned_friends = [int(url.replace('http://darkgoldenrod/api/authors/', '')) for url in friends]

    if not cleaned_followings and not cleaned_friends:
        return render(request, 'feed.html', {'page_obj': [], 'author_id': current_author})

    # print(f"Current Author ID: {current_author}|")  # Debug the current author's ID
    # follower_url = "http://darkgoldenrod/api/authors/" + str(current_author)
    # print(f"Follower URL: {follower_url}|")  # Debug the full follower URL
    # print(f'Author IDs: {followings}|')
    # print(f"Cleaned Author IDs: {cleaned_followings}|")
    # print(f"{public_posts}")

    # Retrieve posts from authors the user is following

    public_posts = Post.objects.filter(visibility__in=['PUBLIC'])

    follow_posts = Post.objects.filter(author__in=cleaned_followings, visibility__in=['PUBLIC', 'UNLISTED'])

    friend_posts = Post.objects.filter(author__in=cleaned_friends, visibility__in=['PUBLIC', 'UNLISTED','FRIENDS'])
    reposts = Repost.objects.filter(shared_by__in=cleaned_followings).order_by('-shared_date')
    cleaned_reposts = []
    for repost in reposts:
        post = repost.original_post
        cleaned_reposts.append({
            "id": post.id,
            "title": post.title,
            "description": post.description,
            "author": post.author,
            "published": post.published,
            "text_content": post.text_content,
            "likes": PostLike.objects.filter(owner=post).count(),
            "comments": Comment.objects.filter(post=post).count(),
            "url": reverse("view_post", kwargs={"post_id": post.id}),
            "shared_by": repost.shared_by,
            "shared_date": repost.shared_date
        })

    # Filter based on the selected option
    if filter_option == "followings":
        posts = (follow_posts | friend_posts).distinct().order_by('-published')
    elif filter_option == "public":
        posts = public_posts.order_by('-published')
    elif filter_option == "friends":
        posts = friend_posts.order_by('-published')
    elif filter_option == "reposts":
        cleaned_posts = cleaned_reposts
    else:  # 'all' filter (default)
        posts = (public_posts | follow_posts | friend_posts).distinct().order_by('-published')


    if filter_option != "reposts":
        cleaned_posts = []
        for post in posts:
            cleaned_posts.append({
                "id": post.id,
                "title": post.title,
                "description": post.description,
                "author": post.author,
                "published": post.published,
                "text_content": post.text_content,
                "likes": PostLike.objects.filter(owner=post).count(),
                "comments": Comment.objects.filter(post=post).count(),
                "url": reverse("view_post", kwargs={"post_id": post.id})
            })

    if filter_option == "all":
        cleaned_posts = cleaned_reposts + cleaned_posts



    # likes = [PostLike.objects.filter(owner=post).count() for post in posts]

    # Pagination setup
    paginator = Paginator(cleaned_posts, 10)  # Show 10 posts per page
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Render the feed template and pass the posts as context
    return render(request, 'feed.html', {'page_obj': page_obj, 'author_id': current_author,})


def repost_post(request, id):
    post = get_object_or_404(Post, pk=id)
    # Only public posts can be shared
    if post.visibility != "PUBLIC":
        return HttpResponseForbidden("Post cannot be shared.")

    shared_post = Repost.objects.create(
        original_post=post,
        shared_by=get_author(request)
    )

    return(redirect(f'/node/posts/{id}/'))

def upload_image(request):
    signed_id = request.COOKIES.get('id')
    id = signing.loads(signed_id)
    author = get_object_or_404(Author, id=id)

    if request.method == 'POST':
        form = ImageUploadForm(request.POST, request.FILES)
        if form.is_valid():
            image = form.save(commit=False)
            image.author = author
            image.save()
            return redirect('index')
    else:
        form = ImageUploadForm()
    return render(request, 'node_admin/upload_image.html', {'form': form})


from django.http import JsonResponse
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def test_auth_view(request):
    return JsonResponse({'message': f'Authenticated as {request.user.email}'})
