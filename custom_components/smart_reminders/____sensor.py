from homeassistant import core
from homeassistant.const import (
    CONF_USERNAME,
    CONF_PASSWORD,
    CONF_PORT,
    CONF_HOST
)
import homeassistant.helpers.config_validation as cv
from homeassistant.components.sensor import PLATFORM_SCHEMA
import voluptuous as vol

CONF_DATABASE = 'database'

PLATFORM_SCHEMA = PLATFORM_SCHEMA.extend(
    {
        vol.Required(CONF_USERNAME): cv.string,
        vol.Required(CONF_PASSWORD): cv.string,
        vol.Required(CONF_PORT): cv.port,
        vol.Required(CONF_HOST): cv.url,
        vol.Required(CONF_DATABASE): cv.string
    }
)


async def async_setup_platform(
    hass: HomeAssistantType,
    config: ConfigType,
    async_add_entities: Callable,
    discovery_info: Optional[DiscoveryInfoType] = None,
) -> None:
    """Set up the sensor platform."""
    postgresql = psycopg2.connect(
        user=config[CONF_USERNAME],
        password=config[CONF_PASSWORD],
        host=config[CONF_HOST],
        port=config[CONF_PORT],
        database=config[CONF_DATABASE])

    sensors = [SmartRemindersSensor(postgresql, hass, config)]
    async_add_entities(sensors, update_before_add=True)


class SmartRemindersSensor(Entity):
    def __init__(self, db: any, hass: HomeAssistantType, config: ConfigType):
        super().__init__()
        self.db = db
        self.hass = hass
        self.config = config
        self._name = config[CONF_DATABASE]
        self._state = None
        self._available = True
        self.data = {}

    @property
    def name(self) -> str:
        """Return the name of the entity"""
        return self._name

    @property
    def unique_id(self) -> str:
        """Return the unique ID of the sensor"""
        # could make this target_user so we can target a user to remind
        return "smart_reminder_{}_{}".format(self.config[CONF_USERNAME], self.config[CONF_DATABASE])

    @property
    def available(self) -> bool:
        """Return True if entity is available."""
        return self._available

    @property
    def state(self) -> Optional[str]:
        return self._state

    @property
    def device_state_attributes(self) -> Dict[str, Any]:
        return self.attrs

    async def async_update(self):
        return
