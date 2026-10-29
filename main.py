
# default main.py from uv init
#def main():
#    print("Hello from fastapi-blog-tutorial!")
#
#if __name__ == "__main__":
#    main()

# App code

from fastapi import FastAPI, Request
#from fastapi.responses import HTMLResponse   # don't need this any more since we are using Jinja2Templates
from fastapi.templating import Jinja2Templates	# templating system for HTML responses
from fastapi.staticfiles import StaticFiles	# to serve static files like CSS, JS, images, etc.

# create app object
app = FastAPI()

# create templates object to use Jinja2Templates for HTML responses
templates = Jinja2Templates(directory="templates")	# tell Jinja2 where to find our HTML templates

# mount the static files directory
app.mount("/static", StaticFiles(directory="static"), name="static")	# tell FastAPI where to find our static files

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




# /api/* routes will return JSON
@app.get("/api/posts")
def get_posts ():
	return posts 	# returning a dictionary or list of dicts will automatically be converted to JSON

