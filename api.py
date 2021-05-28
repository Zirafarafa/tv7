from flask import Blueprint, request, jsonify, redirect, Response, make_response

bp = Blueprint('api', __name__, url_prefix='/api')

# Will be initialized by main.py
tv7 = None

@bp.route('/channels')
def channels():
  tv7.update()

  format = request.args.get('format', 'm3u')
  app = request.args.get('app', 'kodi')
  if format == 'json':
    return jsonify(tv7.channels)
  if format == 'all':
    return jsonify(tv7.all_channels)
  if format == 'm3u':
    response = make_response(tv7.get_m3u(app=app))
    response.mimetype = "text/plain"
    return response
  return jsonify({
    'success': False,
    'message': 'No format given',
  }), 400

@bp.route('/guide')
def guide():
  tv7.update()

  format = request.args.get('format', 'xmltv')
  app = request.args.get('app', 'kodi')

  if format == 'json':
    return jsonify(tv7.channels)

  if format == 'xmltv':
    response = make_response(tv7.get_epg(app=app))
    response.mimetype = "application/xml"
    return response
  return jsonify({
    'success': False,
    'message': 'No format given',
  }), 400

@bp.route('/catchup')
def catchup():
  # Used for apps which cannot correctly format the catchup-source args
  # Redirects to tv7 with the correct start and stop args
  app = request.args.get('app', 'kodi')
  channel = request.args.get('channel')
  start = int(request.args.get('start'))
  duration = int(request.args.get('duration'))

  if start == 0 or duration == 0:
    return "Bad parameters", 400

  url = tv7.get_catchup_url(channel=channel, start=start, duration=duration)
  return redirect(url)
  

@bp.route('/update')
def update():
  force = request.args.get('force', False)
  tv7.update(force=force)

  return jsonify({'success': True})




