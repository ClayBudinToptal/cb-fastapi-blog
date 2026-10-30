
# default main.py from uv init
#def main():
#    print("Hello from fastapi-blog-tutorial!")
#
#if __name__ == "__main__":
#    main()

# App code

# Python dummy data to work with and test our app
#  looks like JSON but JSON would complain about these comments and commas at end of objects
#  the variable posts is defined with its type as a list of dictionaries, which is what we want to return from our API endpoint
posts: list[dict] = [
	{
		"id": 1,
		"author": "Clay Budin",
		"title": "FastAPI is Awesome!",
		"content": "This is an example post for our app.",
		"date_posted": "October 28, 2026",
	},
	{
		"id": 2,
		"author": "Shecky Greene",
		"title": "Another Post",
		"content": "Another example post by a different user.",
		"date_posted": "October 31, 2026",
	},
]


# app imports
from fastapi import FastAPI, Request 			# Request is needed to pass to the template for generating URLs for static files
#from fastapi.responses import HTMLResponse   	# don't need this any more since we are using Jinja2Templates
from fastapi.templating import Jinja2Templates	# templating system for HTML responses
from fastapi.staticfiles import StaticFiles		# to serve static files like CSS, JS, images, etc. - mounted below

from schemas import PostCreate, PostResponse	# import pydantic models for data validation and serialization

# error handling imports
from fastapi import HTTPException, status		# HTTPException is needed to return 404 error, status gives us access to standard HTTP status codes
from fastapi.exceptions import RequestValidationError	# RequestValidationError is needed to handle validation errors and return a custom response
from fastapi.responses import JSONResponse		# JSONResponse is needed to return a custom JSON response for validation errors
# fastapi is built on top of starlette, so we can also import from starlette if needed
from starlette.exceptions import HTTPException as StarletteHTTPException	# needed to handle 404 errors and return a custom response


# create app object
app = FastAPI()

# create templates object to use Jinja2Templates for HTML responses
templates = Jinja2Templates(directory="templates")	# tell Jinja2 where to find our HTML templates

# mount the static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")	# tell FastAPI where to find our static files


# routes are created with decorators
#@app.get("/")
## async def home ():	# could use this if we were doing async stuff, but we are not yet
#def home ():
#	return {"message": "Hello from fastapi-blog-tutorial! home()"}		# returning a dictionary will automatically be converted to JSON

# /* routes return HTML instead of JSON
#@app.get("/", response_class=HTMLResponse, include_in_schema=False)			# stack decorators to have multiple routes for the same function
#@app.get("/posts", response_class=HTMLResponse, include_in_schema=False)	# hide from documentation since this is human, not an API endpoint
#def home ():
#	#return f"<h1>{posts[0]['title']}</h1><p>{posts[0]['content']}</p><p>by {posts[0]['author']} on {posts[0]['date_posted']}</p>"
#	return f"<h1>{posts[0]['title']}</h1>"

# now using templates
@app.get("/", include_in_schema=False, name="home")			# stack decorators to have multiple routes for the same function
@app.get("/posts", include_in_schema=False, name="posts")	# hide from documentation since this is human, not an API endpoint
def home (request: Request):	# need to pass the request object to the template so it can generate URLs for static files
	#return templates.TemplateResponse(request, "home_template.html")	  # return the rendered template (simple - no data passed to template yet)
	#return templates.TemplateResponse(request, "home_template.html", {"posts": posts, "title": "Home"})	# return the rendered template with context dict data
	return templates.TemplateResponse(request, "home_template3.html", {"posts": posts, "title": "Home"})	# now using template inheritance

# display one post based on parameter in the URL path
@app.get("/posts/{post_id}", include_in_schema=False, name="one_post")	# hide from documentation since this is human, not an API endpoint
def one_post (request: Request, post_id: int):	# need to pass the request object to the template so it can generate URLs for static files, and post_id is a path parameter
	for post in posts:
		if post["id"] == post_id:	# could also use post.get("id") == post_id to avoid KeyError if "id" is not in the dict
			title = post["title"][:50] if "title" in post else "Post"	# get the title from the post dict, or use a default value if not found
			return templates.TemplateResponse(request, "post_template.html", {"post": post, "title": title})	# now using template inheritance
		
	# raise an HTTPException with 404 status code and a detail message
	# this will return JSON to the user in the browser which is not good
	raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Post with id {post_id} not found")



# /api/* routes will return JSON
# return all posts as JSON
#@app.get("/api/posts")
#def get_posts ():
#	return posts 	# returning a dictionary or list of dicts will automatically be converted to JSON

# return all posts as JSON using pydantic models for validation and serialization
@app.get("/api/posts", response_model=list[PostResponse], name="get_posts")
def get_posts ():
	return posts 	# automatically validated to conform to schema


# return one post as JSON based on parameter in the URL path
#@app.get("/api/posts/{post_id}")
@app.get("/api/posts/{post_id}", response_model=PostResponse, name="get_post")	# use pydantic model for validation and serialization
def get_post (post_id: int):	# int type hint will automatically validate the path parameter and return a 422 error if it is not an int
	#return posts[post_id - 1] 	# returning a dictionary or list of dicts will automatically be converted to JSON
	for post in posts:
		if post["id"] == post_id:	# could also use post.get("id") == post_id to avoid KeyError if "id" is not in the dict
			return post

	# post id not found
	#return {"error": "Post not found"}	# this is not good - returns 200 OK, should return 404 Not Found instead
	raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"Post with id {post_id} not found")	# raise an HTTPException with 404 status code and a detail message


# Create a new post
# app.post is used to create a new resource, in this case a new post - validates input data against schema
@app.post("/api/posts", response_model=PostResponse, status_code=status.HTTP_201_CREATED, name="create_post")
def create_post (post: PostCreate):
    new_id = max(p["id"] for p in posts) + 1 if posts else 1	# dummy id - database will generate this automatically
    new_post = {
        "id": new_id,
        "author": post.author,
        "title": post.title,
        "content": post.content,
        "date_posted": "April 23, 2025",
    }
    posts.append(new_post)
    return new_post





# exception handlers for custom error responses
# handle 404 errors for HTML responses
# using StarletteHTTPException Handler automatically handles cases where the route is not found like http://127.0.0.1:8000/xxxxx
# fastapi.HTTPException is a subclass so it will also get handled here
@app.exception_handler(StarletteHTTPException)
def general_http_exception_handler (request: Request, exception: StarletteHTTPException):
	# error message
    message = (
        exception.detail
        if exception.detail
        else "An error occurred. Please check your request and try again."
    )

	# if from api route, return JSON response
    if request.url.path.startswith("/api"):
		# this is a simple response for now, should use fastapi response which handles more cases
        return JSONResponse(
            status_code=exception.status_code,
            content={"detail": message},
        )

	# otherwise return HTML response
    return templates.TemplateResponse(
        request,
        "error_template.html",
        {
            "status_code": exception.status_code,
            "title": exception.status_code,
            "message": message,
        },
        status_code=exception.status_code,
    )


### handle validation errors for HTML and JSON responses
@app.exception_handler(RequestValidationError)
def validation_exception_handler (request: Request, exception: RequestValidationError):
    if request.url.path.startswith("/api"):
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
            content={"detail": exception.errors()},
        )
	
    return templates.TemplateResponse(
        request,
        "error_template.html",
        {
            "status_code": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "title": status.HTTP_422_UNPROCESSABLE_CONTENT,
            "message": "Invalid request. Please check your input and try again.",
        },
        status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
    )


