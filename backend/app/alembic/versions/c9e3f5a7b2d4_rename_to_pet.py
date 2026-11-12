"""rename stored ids and values to PET

Revision ID: c9e3f5a7b2d4
Revises: b8d2e4f6a1c3
Create Date: 2026-11-03 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op

revision: str = 'c9e3f5a7b2d4'
down_revision: Union[str, Sequence[str], None] = 'b8d2e4f6a1c3'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

CONTENT_TABLES = ('problems', 'mcq_questions', 'debug_challenges', 'theory_questions',
                  'diagnostic_items')


def _rename(old: dict, new: dict) -> None:
    for table in CONTENT_TABLES:
        op.execute(f"UPDATE {table} SET external_id = REPLACE(external_id, '{old['id']}', "
                   f"'{new['id']}') WHERE external_id LIKE '%{old['id']}%'")
    op.execute(f"UPDATE book_chunks SET source_id = REPLACE(source_id, '{old['guide']}', "
               f"'{new['guide']}') WHERE source_id LIKE '{old['guide']}%'")
    if op.get_bind().dialect.name == 'postgresql':
        op.execute(f"UPDATE chat_messages SET citations = REPLACE(citations::text, "
                   f"'{old['guide']}', '{new['guide']}')::json "
                   f"WHERE citations::text LIKE '%{old['guide']}%'")
    op.execute(f"UPDATE chat_threads SET mode = '{new['mode']}' WHERE mode = '{old['mode']}'")
    op.execute(f"UPDATE llm_calls SET key_source = '{new['key']}' "
               f"WHERE key_source = '{old['key']}'")
    op.execute(f"UPDATE users SET email = '{new['email']}' WHERE email = '{old['email']}'")
    with op.batch_alter_table('chat_threads') as batch:
        batch.alter_column('mode', server_default=new['mode'])
    with op.batch_alter_table('llm_calls') as batch:
        batch.alter_column('key_source', server_default=new['key'])


OLD = {'id': 'aita-', 'guide': 'paet-guide-', 'mode': 'aita', 'key': 'paet',
       'email': 'student@paet.local'}
NEW = {'id': 'pet-', 'guide': 'pet-guide-', 'mode': 'pet', 'key': 'pet',
       'email': 'student@pet.local'}


def upgrade() -> None:
    _rename(OLD, NEW)


def downgrade() -> None:
    _rename(NEW, OLD)
