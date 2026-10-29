#
# file of snippets to be used in the fastapi-blog-tutorial app
#


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


