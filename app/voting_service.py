"""Aturan satu akun satu suara dan rekap suara kandidat."""
from collections import defaultdict
from datetime import datetime, timezone
import inspect
from pymongo.errors import DuplicateKeyError, OperationFailure


ALREADY_VOTED = "Anda sudah memilih. Setiap akun hanya boleh memilih satu kali."


async def init_voting_indexes(db):
    try:
        # Pengecekan find_one saja tidak cukup untuk dua request bersamaan.
        # Suara lama yang belum memiliki voter_id tidak dihapus atau dimodifikasi.
        await db["votings"].create_index(
            "voter_id", name="one_vote_per_user", unique=True,
            partialFilterExpression={"voter_id": {"$type": "string"}})
    except (DuplicateKeyError, OperationFailure) as exc:
        if exc.code == 11000:
            raise RuntimeError(
                "Index satu akun satu suara gagal: terdapat voter_id duplikat di votings. "
                "Jalankan scripts/audit_votes.py dan tinjau data dengan panitia. "
                "Tidak ada suara yang dihapus otomatis.") from exc
        raise
    await db["votings"].create_index("candidate_id")


async def existing_vote(db, user):
    return await db["votings"].find_one({"$or": [
        {"voter_id": str(user["_id"])},
        # Kompatibilitas suara lama yang hanya mencatat nama.
        {"voter_id": None, "voter_name": user["username"]},
    ]})


async def rows(cursor):
    # Motor.aggregate mengembalikan cursor; PyMongo Async.aggregate di-await dulu.
    if inspect.isawaitable(cursor):
        cursor = await cursor
    return [row async for row in cursor]


async def candidate_rankings(db, collection_name):
    candidates = await rows(db[collection_name].find({}, {"name": 1}))
    grouped = await rows(db["votings"].aggregate([
        {"$group": {
            "_id": {"candidate_id": {"$ifNull": ["$candidate_id", None]},
                    "name_candidate": {"$ifNull": ["$name_candidate", None]}},
            "count": {"$sum": 1},
        }},
    ]))
    by_id = defaultdict(int)
    by_legacy_name = defaultdict(int)
    recorded_votes = 0
    for group in grouped:
        recorded_votes += group["count"]
        identity = group["_id"]
        if identity["candidate_id"] is not None:
            by_id[str(identity["candidate_id"]) ] += group["count"]
        else:
            by_legacy_name[identity["name_candidate"]] += group["count"]
    name_frequency = defaultdict(int)
    for candidate in candidates:
        name_frequency[candidate["name"]] += 1
    results = []
    for candidate in candidates:
        name = candidate["name"]
        count = by_id[str(candidate["_id"])]
        # Jangan gandakan suara lama jika ada dua kandidat bernama sama.
        if name_frequency[name] == 1:
            count += by_legacy_name[name]
        results.append({"candidate_id": str(candidate["_id"]), "name": name,
                        "total_votes": count})
    results.sort(key=lambda item: (-item["total_votes"], item["name"].casefold(), item["candidate_id"]))
    total = sum(item["total_votes"] for item in results)
    last_count = None
    rank = 0
    for index, item in enumerate(results, start=1):
        if item["total_votes"] != last_count:
            rank = index
        item["rank"] = rank
        item["percentage"] = round(item["total_votes"] / total * 100, 2) if total else 0.0
        last_count = item["total_votes"]
    return {"data": results, "total_candidates": len(results), "total_votes": total,
            "recorded_votes": recorded_votes, "unmatched_votes": recorded_votes - total,
            "updated_at": datetime.now(timezone.utc)}
