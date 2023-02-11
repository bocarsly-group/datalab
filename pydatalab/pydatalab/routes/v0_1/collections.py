import datetime

from flask import Blueprint, jsonify, request
from flask_login import current_user
from pydantic import ValidationError

from pydatalab.config import CONFIG
from pydatalab.models.collections import Collection
from pydatalab.mongo import flask_mongo
from pydatalab.routes.utils import get_default_permissions
from pydatalab.routes.v0_1.items import creators_lookup, get_samples_summary

collection = Blueprint("collections", __name__)


@collection.route("/collections/")
def get_collections():

    if not current_user.is_authenticated and not CONFIG.TESTING:
        return (
            jsonify(
                status="error",
                message="Authorization required to list collections.",
            ),
            401,
        )

    collections = flask_mongo.db.collections.aggregate(
        [
            {"$match": get_default_permissions(user_only=True)},
            {"$lookup": creators_lookup()},
            {"$project": {"_id": 0}},
            {"$sort": {"_id": -1}},
        ]
    )

    return jsonify({"status": "success", "collections": list(collections)})


@collection.route("/collections/<collection_id>", methods=["GET"])
def get_collection(collection_id: str):

    collection = flask_mongo.db.collections.aggregate(
        [
            {
                "$match": {
                    "collection_id": collection_id,
                    **get_default_permissions(user_only=True),
                }
            },
            {"$lookup": creators_lookup()},
            {"$sort": {"_id": -1}},
        ]
    )

    collection = Collection(**list(collection)[0])

    samples = get_samples_summary(
        match={
            "relationships.type": "collection",
            "relationships.immutable_id": collection.immutable_id,
        }
    )

    return jsonify({"status": "success", "samples": list(samples)})


@collection.route("/collections/", methods=["PUT"])
def create_collection():
    request_json = request.get_json()  # noqa: F821 pylint: disable=undefined-variable
    data = request_json.get("data", {})
    copy_from_id = request_json.get("copy_from_collection_id", None)

    if not current_user.is_authenticated and not CONFIG.TESTING:
        return (
            dict(
                status="error",
                message="Unable to create new collection without user authentication.",
                collection_id=data.get("collection_id"),
            ),
            401,
        )

    if copy_from_id:
        raise NotImplementedError("Copying collections is not yet implemented.")

    if CONFIG.TESTING:
        data["creator_ids"] = []
        data["creators"] = [
            {"display_name": "Public testing user", "contact_email": "datalab@odbx.science"}
        ]
    else:
        data["creator_ids"] = [current_user.person.immutable_id]
        data["creators"] = [
            {
                "display_name": current_user.person.display_name,
                "contact_email": current_user.person.contact_email,
            }
        ]

    # check to make sure that item_id isn't taken already
    if flask_mongo.db.collections.find_one({"collection_id": data["collection_id"]}):
        return (
            dict(
                status="error",
                message=f"collection_id_validation_error: {data['collection_id']!r} already exists in database.",
                collection_id=data["collection_id"],
            ),
            409,  # 409: Conflict
        )

    data["date"] = data.get("date", datetime.datetime.now())

    try:
        data_model = Collection(**data)

    except ValidationError as error:
        return (
            dict(
                status="error",
                message=f"Unable to create new collection with ID {data['collection_id']}.",
                item_id=data["collection_id"],
                output=str(error),
            ),
            400,
        )

    result = flask_mongo.db.collections.insert_one(data_model.dict())
    if not result.acknowledged:
        return (
            dict(
                status="error",
                message=f"Failed to add new collection {data['collection_id']!r} to database.",
                collection_id=data["collection_id"],
                output=result.raw_result,
            ),
            400,
        )

    data_model.num_items = 0

    return (
        {
            "status": "success",
            "data": {data_model.json()},
        },
        201,  # 201: Created
    )


@collection.route("/collections/<collection_id>", methods=["DELETE"])
def delete_collection(collection_id: str):

    if not current_user.is_authenticated and not CONFIG.TESTING:
        return (
            jsonify(
                status="error",
                message="Authorization required to delete collections.",
            ),
            401,
        )

    result = flask_mongo.db.collections.delete_one(
        {"collection_id": collection_id, **get_default_permissions(user_only=True)}
    )

    if result.deleted_count != 1:
        return (
            jsonify(
                {
                    "status": "error",
                    "message": f"Authorization required to attempt to delete collection with {collection_id=} from the database.",
                }
            ),
            401,
        )
    return (
        jsonify(
            {
                "status": "success",
            }
        ),
        200,
    )


@collection.route("/search-collections/", methods=["GET"])
def search_collections():
    query = request.args.get("query", type=str)
    nresults = request.args.get("nresults", default=100, type=int)

    match_obj = {"$text": {"$search": query}, **get_default_permissions(user_only=True)}

    cursor = flask_mongo.db.collections.aggregate(
        [
            {"$match": match_obj},
            {"$sort": {"score": {"$meta": "textScore"}}},
            {"$limit": nresults},
            {
                "$project": {
                    "collection_id": 1,
                    "title": 1,
                }
            },
        ]
    )

    return jsonify({"status": "success", "collections": list(cursor)}), 200