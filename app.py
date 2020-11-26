#----------------------------------------------------------------------------#
# Imports
#----------------------------------------------------------------------------#

import json
import dateutil.parser
import babel
from flask import Flask, render_template, request, Response, flash, redirect, url_for
from flask_moment import Moment
from flask_sqlalchemy import SQLAlchemy
import logging
from logging import Formatter, FileHandler
from flask_wtf import Form
from forms import *

from config import SQLALCHEMY_DATABASE_URI
from flask_migrate import Migrate
from sqlalchemy import func, DateTime
import datetime
#----------------------------------------------------------------------------#
# App Config.
#----------------------------------------------------------------------------#

app = Flask(__name__)
moment = Moment(app)
app.config.from_object('config')
db = SQLAlchemy(app)

# Connect to a local postgresql database
app.config['SQLALCHEMY_DATABASE_URI'] = SQLALCHEMY_DATABASE_URI
migrate = Migrate(app, db)

#----------------------------------------------------------------------------#
# Models.
#----------------------------------------------------------------------------#

class Venue(db.Model):
    __tablename__ = 'Venue'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    address = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    image_link = db.Column(db.String(500), default=None)
    genres = db.Column(db.String(500))
    facebook_link = db.Column(db.String(120))
    seeking_talent = db.Column(db.Boolean, default=False)
    seeking_description = db.Column(db.String(500))
    show_id = db.relationship('Show', backref='venue', lazy=True)
    # TODO: implement any missing fields, as a database migration using Flask-Migrate

    def __repr__(self):
        return 'Venue: {}'.format(self.name)


class Artist(db.Model):
    __tablename__ = 'Artist'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String)
    city = db.Column(db.String(120))
    state = db.Column(db.String(120))
    phone = db.Column(db.String(120))
    genres = db.Column(db.String(120))
    image_link = db.Column(db.String(500), default=None)
    facebook_link = db.Column(db.String(120))
    seeking_venue = db.Column(db.Boolean, default=False)
    seeking_description = db.Column(db.String(500))

    #"past_shows"
    #"upcoming_shows": [],
    past_shows_count = db.Column(db.Integer, default=0)
    upcoming_shows_count = db.Column(db.Integer, default=0)
    show_id = db.relationship('Show', backref='artist', lazy=True)
    # TODO: implement any missing fields, as a database migration using Flask-Migrate

    def __repr__(self):
      return 'Artist {}'.format(self.name)

class Show(db.Model):
  __tablename__ = 'Show'

  id = db.Column(db.Integer, primary_key=True)
  name = db.Column(db.String)
  start_time = db.Column(DateTime, default=datetime.datetime.utcnow)
  #start_time = db.Column(db.String(500))
  image_link = db.Column(db.String(500), default=None)
  artist_id = db.Column(db.Integer, db.ForeignKey('Artist.id'), nullable=False)
  venue_id =  db.Column(db.Integer, db.ForeignKey('Venue.id'), nullable=False)

# TODO Implement Show and Artist models, and complete all model relationships and properties, as a database migration.
db.create_all()

#----------------------------------------------------------------------------#
# Filters.
#----------------------------------------------------------------------------#

def format_datetime(value, format='medium'):
  #date = dateutil.parser.parse(value)

  if isinstance(value, str):
    date = dateutil.parser.parse(value)
  else:
    date = value
      
  if format == 'full':
      format="EEEE MMMM, d, y 'at' h:mma"
  elif format == 'medium':
      format="EE MM, dd, y h:mma"
  return babel.dates.format_datetime(date, format)

app.jinja_env.filters['datetime'] = format_datetime

#----------------------------------------------------------------------------#
# Controllers.
#----------------------------------------------------------------------------#

@app.route('/')
def index():
  return render_template('pages/home.html')

#----------------------------------------------------------------------------#
#  Venues
#  ----------------------------------------------------------------

@app.route('/venues')
def venues():
  cities = []
  states = []
  venues = Venue.query.order_by(Venue.city).all()
  for venue in venues:
    if venue.city not in cities:
      cities.append(venue.city)
      states.append(venue.state)
    else:
      indices = [i for i, x in enumerate(cities) if x == venue.city]
      for index in indices:
        if venue.state == states[index]:
          break
        cities.append(venue.city)
        states.append(venue.state)
  
  data = []
  for i, city in enumerate(cities):
    venues = venue.query.filter(Venue.city==city, Venue.state==states[i]).all()
    temp = {
      "city": city,
      "state": states[i],
      "venues": []
    }
    for venue in venues:
      venue.num_upcoming_shows = Show.query.filter(Show.start_time>datetime.datetime.now()).count()
      temp['venues'].append(venue)
    data.append(temp)

  return render_template('pages/venues.html', areas=data)

@app.route('/venues/search', methods=['POST'])
def search_venues():
  data = Venue.query.filter(Venue.name.ilike("%"+request.form.get('search_term', '')+"%")).all()

  response={
    "count": len(data),
    "data": data
  }
  return render_template('pages/search_venues.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/venues/<int:venue_id>')
def show_venue(venue_id):
  # shows the venue page with the given venue_id
  data = Venue.query.filter_by(id=venue_id).first()
  data.genres = data.genres.strip('}{').split(',')
  data.upcoming_shows = Show.query.filter_by(venue_id=data.id).all()
  data.past_shows_count = Show.query.filter(Show.venue_id==data.id, Show.start_time<datetime.datetime.now()).count() #getnum, filter by date
  data.upcoming_shows_count = Show.query.filter(Show.venue_id==data.id, Show.start_time>datetime.datetime.now()).count() #getnum, filter by date

  return render_template('pages/show_venue.html', venue=data)

#  Create Venue
#  ----------------------------------------------------------------

@app.route('/venues/create', methods=['GET'])
def create_venue_form():
  form = VenueForm()
  return render_template('forms/new_venue.html', form=form)

@app.route('/venues/create', methods=['POST'])
def create_venue_submission():
  try:
    venue = Venue(name = request.form['name'], 
                  city = request.form['city'], 
                  state = request.form['state'], 
                  genres = request.form.getlist('genres'), 
                  address = request.form['address'], 
                  phone = request.form['phone'], 
                  facebook_link = request.form['facebook_link'])
    db.session.add(venue)
    db.session.commit()
    flash('Venue ' + request.form['name'] + ' was successfully listed!')
  except:
    db.session.rollback()
    flash('An error occurred. Venue ' + request.form['name'] + ' could not be listed.')
  finally:
    db.session.close()
    return render_template('pages/home.html')

@app.route('/venues/<venue_id>', methods=['DELETE'])
def delete_venue(venue_id):
  # SQLAlchemy ORM to delete a record. Handle cases where the session commit could fail.
  try:
    data = Venue.query.filter_by(id=venue_id)
    data.delete()
    db.session.commit()
  except:
    db.session.rollback()
  finally:
    db.session.close()

  # BONUS CHALLENGE: Implement a button to delete a Venue on a Venue Page, have it so that
  # clicking that button delete it from the db then redirect the user to the homepage
  return None

#  Artists
#  ----------------------------------------------------------------
@app.route('/artists')
def artists():
  data = Artist.query.order_by(Artist.id).all()

  return render_template('pages/artists.html', artists=data)

@app.route('/artists/search', methods=['POST'])
def search_artists():
  data = Artist.query.filter(Artist.name.ilike("%"+request.form.get('search_term', '')+"%")).all()
  
  response={
    "count": len(data),
    "data": data
  }
  
  return render_template('pages/search_artists.html', results=response, search_term=request.form.get('search_term', ''))

@app.route('/artists/<int:artist_id>')
def show_artist(artist_id):
  # shows the venue page with the given venue_id
  data = Artist.query.filter_by(id=artist_id).first()
  data.genres = data.genres.strip('}{').split(',')
  data.past_shows = Show.query.filter(Show.artist_id==data.id, Show.start_time<datetime.datetime.now()).all()
  data.upcoming_shows = Show.query.filter(Show.artist_id==data.id, Show.start_time>datetime.datetime.now()).all()
  data.past_shows_count = Show.query.filter(Show.artist_id==data.id, Show.start_time<datetime.datetime.now()).count()
  data.upcoming_shows_count = Show.query.filter(Show.artist_id==data.id, Show.start_time>datetime.datetime.now()).count()
 
  return render_template('pages/show_artist.html', artist=data)

#  Update
#  ----------------------------------------------------------------
@app.route('/artists/<int:artist_id>/edit', methods=['GET'])
def edit_artist(artist_id):
  form = ArtistForm()
  artist = Artist.query.filter_by(id=artist_id).first()
  form.name.data = artist.name
  form.genres.data = artist.genres
  form.city.data = artist.city
  form.state.data = artist.state
  form.phone.data = artist.phone
  form.facebook_link.data = artist.facebook_link

  return render_template('forms/edit_artist.html', form=form, artist=artist)

@app.route('/artists/<int:artist_id>/edit', methods=['POST'])
def edit_artist_submission(artist_id):
  # TODO: take values from the form submitted, and update existing
  # artist record with ID <artist_id> using the new attributes
  try:
    artist = Artist.query.filter_by(id=artist_id).first()
    artist.name = request.form['name']
    artist.genres = request.form.getlist('genres')
    artist.city = request.form['city']
    artist.state = request.form['state']
    artist.phone = request.form['phone']
    artist.facebook_link = request.form['facebook_link']
    db.session.commit()
    flash('Artist ' + request.form['name'] + ' was successfully edited!')
  except:
    db.session.rollback()
    flash('Artist ' + request.form['name'] + ' could not be edited!')
  finally:
    db.session.close()
    return redirect(url_for('show_artist', artist_id=artist_id))

@app.route('/venues/<int:venue_id>/edit', methods=['GET'])
def edit_venue(venue_id):
  venue = Venue.query.filter_by(id=venue_id).first()
  form = VenueForm()
  form.name = venue.name
  form.genres = venue.genres
  form.address = venue.address
  form.city = venue.city
  form.state = venue.state
  form.phone = venue.phone
  form.facebook_link = venue.facebook_link

  return render_template('forms/edit_venue.html', form=form, venue=venue)

@app.route('/venues/<int:venue_id>/edit', methods=['POST'])
def edit_venue_submission(venue_id):
  # venue record with ID <venue_id> using the new attributes
  try:
    venue = Venue.query.filter_by(id=venue_id).first()
    venue.name = request.form['name']
    venue.genres = request.form.getlist('genres')
    venue.address = request.form['address']
    venue.city = request.form['city']
    venue.state = request.form['state']
    venue.phone = request.form['phone']
    venue.facebook_link = request.form['facebook_link']
    db.session.commit()
    flash('Venue ' + request.form['name'] + ' was successfully edited!')
  except:
    db.session.rollback()
    flash('Venue ' + request.form['name'] + ' was successfully edited!') 
  finally:
    db.session.close()
    return redirect(url_for('show_venue', venue_id=venue_id))

#  Create Artist
#  ----------------------------------------------------------------

@app.route('/artists/create', methods=['GET'])
def create_artist_form():
  form = ArtistForm()
  return render_template('forms/new_artist.html', form=form)

@app.route('/artists/create', methods=['POST'])
def create_artist_submission():
  # called upon submitting the new artist listing form
  artist = Artist(name=request.form['name'],
                  city=request.form['city'],
                  state=request.form['state'],
                  phone=request.form['phone'],
                  genres=request.form.getlist('genres'),
                  facebook_link=request.form['facebook_link'])
  try:
    db.session.add(artist)
    db.session.commit()
    flash('Artist ' + request.form['name'] + ' was successfully listed!')
  except:
    db.session.rollback()
    flash('An error occurred. Artist ' + request.form['name'] + ' could not be listed.')
  finally:
    db.session.close()
    return render_template('pages/home.html')


#  Shows
#  ----------------------------------------------------------------

@app.route('/shows')
def shows():
  # displays list of shows at /shows
  shows = Show.query.order_by(Show.start_time).all()
  data = []
  for show in shows:
    data.append({
    "venue_id": show.venue_id,
    "venue_name": show.venue.name,
    "artist_id": show.artist_id,
    "artist_name": show.artist.name,
    "artist_image_link": show.artist.image_link,
    "start_time": show.start_time.strftime('%Y-%m-%d %H:%M:%S')
  })

  return render_template('pages/shows.html', shows=data)

@app.route('/shows/create')
def create_shows():
  # renders form. do not touch.
  form = ShowForm()

  return render_template('forms/new_show.html', form=form)

@app.route('/shows/create', methods=['POST'])
def create_show_submission():
  # called to create new shows in the db, upon submitting new show listing form

  try:
    show = Show(artist_id = request.form['artist_id'],
                venue_id = request.form['venue_id'],
                start_time = request.form['start_time'])
    db.session.add(show)
    db.session.commit()
    flash('Show was successfully listed!')
  except:
    db.session.rollback()
    flash('An error occurred. Show could not be listed.')
  finally:
    db.session.close()
    return render_template('pages/home.html')

  return render_template('pages/home.html')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def server_error(error):
    return render_template('errors/500.html'), 500


if not app.debug:
    file_handler = FileHandler('error.log')
    file_handler.setFormatter(
        Formatter('%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]')
    )
    app.logger.setLevel(logging.INFO)
    file_handler.setLevel(logging.INFO)
    app.logger.addHandler(file_handler)
    app.logger.info('errors')

#----------------------------------------------------------------------------#
# Launch.
#----------------------------------------------------------------------------#

# Default port:
if __name__ == '__main__':
    app.run()

# Or specify port manually:
'''
if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
'''
