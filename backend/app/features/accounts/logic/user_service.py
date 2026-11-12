from sqlalchemy.orm import Session, joinedload
from fastapi import HTTPException, status

from app.features.onboarding.models import OnboardingRecord
from app.features.accounts.models import User, LearningProfile
from app.features.accounts.schemas import UpdateProfileRequest


class UserService:

    @staticmethod
    def get_user_by_id(db: Session, user_id: int) -> User:
        user = (
            db.query(User)
            .options(joinedload(User.learning_profile))
            .filter(User.id == user_id)
            .first()
        )
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")
        return user

    @staticmethod
    def update_profile(db: Session, user_id: int, data: UpdateProfileRequest) -> User:
        user = db.query(User).filter(User.id == user_id).first()
        if not user:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found.")

        update_data = data.model_dump(exclude_unset=True)
        language = update_data.get("preferred_language", user.preferred_language)
        record = db.get(OnboardingRecord, user.id)
        if language != user.preferred_language and record and record.language_locked_at:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail="Use the language switch on your profile to change language."
            )
        for field, value in update_data.items():
            setattr(user, field, value)

        # Recalculate profile completeness
        UserService._update_profile_completeness(db, user)

        db.commit()
        db.refresh(user)
        return user

    @staticmethod
    def _update_profile_completeness(db: Session, user: User):
        """Calculate what % of the profile is filled in."""
        profile = db.query(LearningProfile).filter(LearningProfile.user_id == user.id).first()
        if not profile:
            return

        fields_filled = 0
        total_fields = 8

        if user.full_name: fields_filled += 1
        if user.bio: fields_filled += 1
        if user.institution: fields_filled += 1
        if user.city: fields_filled += 1
        if user.preferred_languages: fields_filled += 1
        if user.learning_goals: fields_filled += 1
        if user.interests: fields_filled += 1
        if user.skill_level: fields_filled += 1

        profile.profile_completeness = round((fields_filled / total_fields) * 100, 1)
        db.flush()

    @staticmethod
    def get_all_users(db: Session, skip: int = 0, limit: int = 50):
        return (
            db.query(User)
            .options(joinedload(User.learning_profile))
            .offset(skip)
            .limit(limit)
            .all()
        )