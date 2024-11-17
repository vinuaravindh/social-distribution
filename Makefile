init:
	touch Procfile
	echo "web: gunicorn socialdistribution.wsgi --chdir Social-Distribution/socialdistribution" > Procfile

	heroku git:remote -a darkgoldenrod
	heroku addons:create heroku-postgresql:essential-0 --app darkgoldenrod
	heroku run "env" --app darkgoldenrod
	heroku buildpacks:set heroku/python --app darkgoldenrod

	echo "python-3.11" > runtime.txt

	git add .
	git commit -m "Add runtime.txt for Python version"
	git push heroku Development:main

	heroku run "python Social-Distribution/socialdistribution/manage.py diffsettings" --app darkgoldenrod
	heroku run "python Social-Distribution/socialdistribution/manage.py migrate" --app darkgoldenrod
	heroku run "python Social-Distribution/socialdistribution/manage.py createsuperuser" --app darkgoldenrod

deploy:
	git add .
	git commit -m "Deploy"
	git push heroku Development:main