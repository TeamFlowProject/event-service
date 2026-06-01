from loguru import logger
from opentelemetry import trace
import uuid

from src.service.track.protocols import KafkaProducer, TrackRepository
from src.models.track import Track
from src.service.tracing import trace_business_logic
import src.adapters.repository.errors as adapter_errors
import src.service.errors as service_errors

tracer = trace.get_tracer(__name__)


class TrackService:
    def __init__(
        self,
        track_repository: TrackRepository,
        kafka_producer: KafkaProducer,
    ) -> None:
        self._track_repository = track_repository
        self._kafka_producer = kafka_producer

    @trace_business_logic("track_service")
    async def create_track(self, track: Track) -> uuid.UUID:
        """
        Create a new track

        Args:
            track (Track): The track to create

        Returns:
            uuid.UUID: The ID of the created track

        Raises:
            EventNotFoundError: If the referenced event does not exist
        """
        span = trace.get_current_span()
        span.set_attribute("track.id", str(track.id))
        span.set_attribute("event.id", str(track.event_id))

        logger.info(
            "service_creating_track",
            track_id=str(track.id),
            event_id=str(track.event_id),
            track_name=track.name,
        )

        try:
            await self._track_repository.create_track(track)
        except adapter_errors.EventNotFoundError as e:
            logger.warning(
                "service_track_create_event_not_found",
                track_id=str(track.id),
                event_id=str(track.event_id),
                error=str(e),
            )
            raise service_errors.EventNotFoundError("Event not found") from e

        await self._kafka_producer.send_create_track(track)

        logger.info("service_track_created", track_id=str(track.id))
        return track.id

    @trace_business_logic("track_service")
    async def update_track(self, track: Track) -> None:
        """
        Update an existing track

        Updates full state of the track including all roles

        Args:
            track (Track): The track to update

        Raises:
            TrackNotFoundError: If the track could not be updated
        """
        span = trace.get_current_span()
        span.set_attribute("track.id", str(track.id))

        logger.info("service_updating_track", track_id=str(track.id))

        try:
            await self._track_repository.update_track(track)
            await self._kafka_producer.send_update_track(track)
            logger.info("service_track_updated", track_id=str(track.id))
        except adapter_errors.TrackNotFoundError as e:
            logger.warning(
                "service_track_update_not_found",
                track_id=str(track.id),
                error=str(e),
            )
            raise service_errors.TrackNotFoundError("Failed to update track") from e

    @trace_business_logic("track_service")
    async def delete_track(self, track_id: uuid.UUID) -> None:
        """
        Delete an existing track

        Args:
            track_id (uuid.UUID): The ID of the track to delete

        Raises:
            TrackNotFoundError: If the track could not be deleted
        """
        span = trace.get_current_span()
        span.set_attribute("track.id", str(track_id))

        logger.info("service_deleting_track", track_id=str(track_id))

        try:
            track = await self._track_repository.get_track(track_id)
            await self._track_repository.delete_track(track_id)
            await self._kafka_producer.send_delete_track(track)
            logger.info("service_track_deleted", track_id=str(track_id))
        except adapter_errors.TrackNotFoundError as e:
            logger.warning(
                "service_track_delete_not_found",
                track_id=str(track_id),
                error=str(e),
            )
            raise service_errors.TrackNotFoundError("Failed to delete track") from e

    @trace_business_logic("track_service")
    async def get_track(self, track_id: uuid.UUID) -> Track:
        """
        Get a track by ID

        Args:
            id (uuid.UUID): The ID of the track to get

        Returns:
            Track: The track with the given ID

        Raises:
            TrackNotFoundError: If the track could not be found
        """
        span = trace.get_current_span()
        span.set_attribute("track.id", str(track_id))

        logger.info("service_receiving_track", track_id=str(track_id))

        try:
            track = await self._track_repository.get_track(track_id)
            logger.info("service_track_received", track_id=str(track_id))
            return track
        except adapter_errors.TrackNotFoundError as e:
            logger.warning(
                "service_track_get_not_found",
                track_id=str(track_id),
                error=str(e),
            )
            raise service_errors.TrackNotFoundError("Failed to get track") from e

    @trace_business_logic("track_service")
    async def get_tracks_by_event_id(self, event_id: uuid.UUID) -> list[Track]:
        """
        Get all tracks for an event

        Args:
            event_id (uuid.UUID): The ID of the event to get tracks for

        Returns:
            list[Track]: The tracks for the event, empty list if event has no tracks
        """
        span = trace.get_current_span()
        span.set_attribute("event.id", str(event_id))

        logger.info("service_receiving_tracks_by_event", event_id=str(event_id))

        tracks = await self._track_repository.get_tracks_by_event_id(event_id)

        logger.info(
            "service_tracks_received",
            event_id=str(event_id),
            count=len(tracks),
        )
        return tracks
