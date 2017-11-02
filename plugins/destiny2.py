import sys
import traceback

from cloudbot import hook
from . import destiny_manifest


@hook.periodic(24 * 60 * 60, initial_interval=10)
def check_manifest(bot):
	api_key = bot.config.get('api_keys', {}).get('destiny', None)
	conn = bot.connections["DTG"]
	current = False
	try:
		current = destiny_manifest.is_manifest_current(api_key)
	except Exception as e:
		exc_type, exc_value, exc_traceback = sys.exc_info()
		traceback.print_exception(exc_type, exc_value, exc_traceback,
                          limit=2, file=sys.stdout)
		conn.message("#DTGCoding", "Error! {}".format(e))

	if not current:
		try:
			result = destiny_manifest.gen_manifest_pickle(api_key)
		except Exception as e:
			exc_type, exc_value, exc_traceback = sys.exc_info()
			traceback.print_exception(exc_type, exc_value, exc_traceback,
                              limit=2, file=sys.stdout)
			conn.message("#DTGCoding", "Error! {}".format(e))
		else:
			conn.message("#DTGCoding", result)
