from src.service.track.protocols import KafkaProducer, TrackRepository
from src.models.track import Track
import uuid
import src.adapters.repository.errors as adapter_errors
import src.service.errors as service_errors


class TrackService:
    def __init__(
        self,
        track_repository: TrackRepository,
        kafka_producer: KafkaProducer,
    ) -> None:
        self._track_repository = track_repository
        self._kafka_producer = kafka_producer

    async def create_track(self, track: Track) -> uuid.UUID:
        """
        Create a new track

        Args:
            track (Track): The track to create

        Returns:
            uuid.UUID: The ID of the created track

        Raises:
            TrackNotFoundError: If the track could not be created
        """

        await self._track_repository.create_track(track)
        await self._kafka_producer.send_create_track(track)

        return track.id

    async def update_track(self, track: Track) -> None:
        """
        Update an existing track

        Updates full state of the track including all roles

        Args:
            track (Track): The track to update

        Raises:
            TrackNotFoundError: If the track could not be updated
        """

        try:
            await self._track_repository.update_track(track)
            await self._kafka_producer.send_update_track(track)
        except adapter_errors.TrackNotFoundError as e:
            raise service_errors.TrackNotFoundError("Failed to update track") from e

    async def delete_track(self, track_id: uuid.UUID) -> None:
        """
        Delete an existing track

        Args:
            id (uuid.UUID): The ID of the track to delete

        Raises:
            TrackNotFoundError: If the track could not be deleted
        """

        try:
            await self._track_repository.delete_track(track_id)
            await self._kafka_producer.send_delete_track(track_id)
        except adapter_errors.TrackNotFoundError as e:
            raise service_errors.TrackNotFoundError("Failed to delete track") from e

    async def get_track(self, track_id: uuid.UUID) -> Track:
        """
        Get a track by ID

        Args:
            id (uuid.UUID): The ID of the track to get

        Returns:
            Track: The track with the given ID

        Raises:
            TrackNotFoundError: If the track could not be found
            RoleNotFoundError: If a role could not be found
        """

        try:
            return await self._track_repository.get_track(track_id)
        except adapter_errors.TrackNotFoundError as e:
            raise service_errors.TrackNotFoundError("Failed to get track") from e

    async def get_tracks_by_event_id(self, event_id: uuid.UUID) -> list[Track]:
        """
        Get all tracks for an event

        Args:
            event_id (uuid.UUID): The ID of the event to get tracks for

        Returns:
            list[Track]: The tracks for the event

        Raises:
            EventNotFoundError: If the event could not be found
            RoleNotFoundError: If a role could not be found
        """

        try:
            return await self._track_repository.get_tracks_by_event_id(event_id)
        except adapter_errors.EventNotFoundError as e:
            raise service_errors.EventNotFoundError("Failed to get tracks") from e
