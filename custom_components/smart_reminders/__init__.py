import psycopg2
import logging
import traceback
import re

from .const import DOMAIN
from datetime import timedelta, datetime

from homeassistant.const import (
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_HOST
)
from homeassistant.helpers.entity import Entity
from homeassistant.helpers.entity_component import EntityComponent
from homeassistant.util import Throttle

_LOGGER = logging.getLogger(__name__)

MIN_TIME_BETWEEN_UPDATES = timedelta(seconds=30)

ATTR_TITLE = 'title'
ATTR_DESC = 'description'
ATTR_DUE = 'due_date'
ATTR_PRIORITY = 'priority'


CONF_DATABASE = 'database'

CONST_LEADING_ENTITY_NAME = 'reminder_'


def setup(hass, config):
    """Set up is called when Home Assistant is loading our component."""

    conf = config[DOMAIN]
    hass.data[DOMAIN] = {}
    reminders = SmartReminders(hass, conf)

    # Return boolean to indicate that initialization was successfully.
    return True


class SmartReminders:
    """Main Smart Reminders Service"""

    def __init__(self, hass, config):
        self.hass = hass
        self.conf = config
        self.db = SmartReminderDB(config)

        items = []
        try:
            self.items = self.db.get_all_reminders()
        except:
            self.items = []

        self.component = EntityComponent(_LOGGER, DOMAIN, hass)
        entities = []

        if self.items:
            for item in self.items:
                ent = SmartReminderItem(hass, item, self.db)
                entities.append(ent)
            if entities:
                self.component.add_entities(entities)

        hass.services.register(DOMAIN, "add_task", self.handle_add_task)
        hass.services.register(DOMAIN, "complete_task", self.handle_complete_task)
        hass.services.register(DOMAIN, "delete_task", self.handle_delete_task)

    async def handle_add_task(self, call):
        """Handle the service call."""
        await self.add_task(call.data)

    async def handle_delete_task(self, call):
        try:
            entity_id = call.data.get('id')
            ent = self.component.get_entity(entity_id)
            idx = ent._id
            await self.db.delete_reminder(idx)
            await self.component.async_remove_entity(entity_id)
        except Exception as e:
            logging.error(traceback.format_exc())

    async def handle_complete_task(self, call):
        """Handle completing the task and removing it from entities"""
        try:
            entity_id = call.data.get('id')
            ent = self.component.get_entity(entity_id)
            idx = ent._id
            self.db.complete_reminder(idx)
            if ent.is_repeatable:
                derp = {ent._repeat_type: ent._repeat_number}
                due_date = ent._original_due_date + timedelta(**derp)
                data = {
                    ATTR_TITLE: ent._title,
                    "user": ent._username,
                    ATTR_DUE: due_date,
                    "repeat_type": ent._repeat_type,
                    "repeat_number": ent._repeat_number,
                    "repeatable": True
                }
                await self.add_task(data)
            await self.component.async_remove_entity(entity_id)
        except Exception as e:
            logging.error(traceback.format_exc())

    async def add_task(self, data):
        try:
            new_item = await self.db.add_reminder(data)
            ent = SmartReminderItem(self.hass, new_item, self.db)
            await self.component.async_add_entities([ent])
        except Exception as e:
            logging.error(traceback.format_exc())


class SmartReminderItem(Entity):
    """An individual Smart Reminder"""

    def __init__(self, hass, data, db):
        self.hass = hass

        self._title = data[0]
        self._due = data[1]
        self._priority = data[2]
        self._completed = data[3]
        self._id = data[4]
        self._username = data[5]
        self._ignore_count = data[6] if data[6] is not None else 0
        self._repeat_type = data[7]
        self._repeat_number = data[8]
        self._original_due_date = data[9]
        self._db = db
        self._overdue = self.is_overdue()

    def is_overdue(self, _overdue=False):
        now = datetime.now()
        overdue = _overdue
        if now >= self._due and not _overdue:
            overdue = True
            message = "{}, I'm reminding you to {}".format(self._username, self._title)
            self.hass.services.call("tts", "google_translate_say", {
                'entity_id': 'all',
                'message': message
            })
            new_time = datetime.now() + timedelta(hours=1)
            self._db.set_due_time(self._id, new_time, self._ignore_count)
            self._due = new_time
        elif now <= self._due and _overdue:
            overdue = False
        return overdue

    @ property
    def is_repeatable(self):
        return self._repeat_type is not None and self._repeat_number > 0

    @ property
    def name(self):
        return "{}{}".format(CONST_LEADING_ENTITY_NAME, self._id)

    @ property
    def state_attributes(self):
        """Returns the name of the reminder"""
        return {
            "title": self._title,
            "due": self._due,
            "completed": self._completed,
            "user": self._username,
            "ignore_count": self._ignore_count,
            "repeatable": self.is_repeatable,
            "repeats": "Repeats every {}{}".format(self._repeat_number, self._repeat_type),
        }

    @ property
    def state(self):
        return self._overdue

    def update(self):
        try:
            self._overdue = self.is_overdue(self._overdue)
        except Exception as e:
            logging.error(traceback.format_exc())


class SmartReminderDB:
    """Interface with Postgresql"""

    def __init__(self, config):
        self.psql = psycopg2.connect(
            user=config.get(CONF_USERNAME),
            password=config.get(CONF_PASSWORD),
            host=config.get(CONF_HOST),
            port=config.get(CONF_PORT),
            database=config.get(CONF_DATABASE))

    def get_all_reminders(self):
        cursor = self.psql.cursor()
        cursor.execute("""select * from reminders where completed = false""")
        items = cursor.fetchall()
        cursor.close()
        return items

    async def add_reminder(self, data):
        cursor = self.psql.cursor()
        is_repeatable = data.get('repeatable')
        repeat_type = data.get('repeat_type') if is_repeatable else ''
        repeat_number = data.get('repeat_number') if is_repeatable else 0
        cursor.execute("""INSERT INTO reminders (title, due_date, username, repeat_type, repeat_number, original_due_date) VALUES (%s, %s, %s, %s, %s, %s) RETURNING *""",
                       (data.get(ATTR_TITLE), data.get(ATTR_DUE), data.get('user'), repeat_type, repeat_number, data.get(ATTR_DUE)))
        item = cursor.fetchone()
        self.psql.commit()
        cursor.close()

        return item

    def complete_reminder(self, idx):
        cursor = self.psql.cursor()
        cursor.execute("""UPDATE reminders SET completed=true WHERE id=%s""", [idx])
        self.psql.commit()
        cursor.close()

    async def delete_reminder(self, idx):
        cursor = self.psql.cursor()
        cursor.execute("""DELETE FROM reminders WHERE id=%s""", [idx])
        self.psql.commit()
        cursor.close()
        return True

    def set_due_time(self, idx, due_date, ct=0):
        cursor = self.psql.cursor()
        new_count = ct + 1
        cursor.execute("""UPDATE reminders SET due_date=%s, ignore_count=%s WHERE id=%s""", [due_date, new_count, idx])
        self.psql.commit()
        cursor.close()
