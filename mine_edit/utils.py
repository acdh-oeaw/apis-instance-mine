import logging
import pathlib
import os
import csv

logger = logging.getLogger(__name__)


def user_edit_permissions(user, obj):
    env = os.environ.get("AUTH_LDAP_USER_PERMISSIONS_LIST", "")
    if env.startswith("file://"):
        try:
            username = user.username if hasattr(user, "username") else str(user)
            obj_id = str(obj.id) if hasattr(obj, "id") else str(obj)

            file_path = pathlib.Path.from_uri(env)
            with open(file_path, "r", newline="") as csvfile:
                reader = csv.reader(csvfile)
                for row in reader:
                    if len(row) >= 2:
                        csv_username = row[0].strip()
                        csv_object_id = row[1].strip()
                        if csv_username == username and csv_object_id == obj_id:
                            return True
            return False
        except Exception as e:
            logger.debug("Error reading user permissions from CSV file: %s", e)
            return False
    else:
        logger.debug("Invalid AUTH_LDAP_USER_PERMISSIONS_LIST environment variable")
        return False
