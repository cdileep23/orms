from django.contrib.contenttypes.models import ContentType
from core.models import RatingModel,CommentModel,RestaurantModel

def run():
    # content_type = ContentType.objects.filter(app_label='core')
    # print([c.model for c in content_type])

    
    # content_type = ContentType.objects.get(app_label='core', model='restaurantmodel')
    
    #get actual model

    # restaurant_model=content_type.model_class()

    # print(restaurant_model)
    # restuarants=content_type.get_object_for_this_type(name='Taco Bell')
    # print(restuarants)

    # rating_content_type=ContentType.objects.get_for_model(RatingModel)
    # print(rating_content_type.model_class())

    # comments=CommentModel.objects.all()
    # for c in comments:
    #     print(c.content_object)

    """
    get the stored content type for the first comment
    """

    """
    grab the first comment row from the table
    """
    # comment=CommentModel.objects.first()

    """
    comment.content_type points to the ContentType row that says
    WHICH model this comment is attached to (e.g. restaurantmodel)
    """
    # ctype=comment.content_type

    """
    model_class() turns that ContentType row back into the real
    model class, e.g. <class 'core.models.RestaurantModel'>
    """
    # print(ctype.model_class())

    """
    from content type fetch the associated foreign key
    """

    """
    we now know the model (ctype) and the row id (comment.object_id),
    so fetch that exact object. get_object_for_this_type is a shortcut for
    ctype.model_class().objects.get(pk=comment.object_id)
    """
    # res=ctype.get_object_for_this_type(pk=comment.object_id)

    """
    res is the actual object the comment was left on, e.g. <RestaurantModel: Taco Bell>
    """
    # print(res)


    """
    pick any object we want to attach a comment to (here, the first restaurant)
    """
    # res=RestaurantModel.objects.first()

    """
    create a comment on that object. we only pass content_object=res and Django
    automatically fills in content_type (restaurantmodel) and object_id (res.id)
    behind the scenes — this is the easy way to write a generic relation
    """
    # comment=CommentModel.objects.create(
    #     text='This is a comment',
    #     content_object=res
    # )

    """
    print(comment) uses the model's __str__, so it shows a readable label
    """
    # print(comment)

    """
    __dict__ shows the raw column values actually stored in the row, so here
    you can SEE the content_type_id and object_id that Django filled in for you
    """
    # print(comment.__dict__)
    
    # restaurants=RestaurantModel.objects.get(id=2)

    """
    bulk=False tells Django to save the new CommentModel first, then attach it.
    without it, .add() expects an already-saved object and raises the
    "instance isn't saved" error you just hit
    """
    # restaurants.comments.add(
    #     CommentModel(
    #         text='This is a comment',
    #         content_object=restaurants
    #     ),
    #     bulk=False
    # )
    # print(restaurants.comments.all())
    """
    grab the most recently added comment on this restaurant.
    .last() returns the final row by the model's ordering (or insertion order)
    """
    # last_comments=restaurants.comments.last()

    """
    detach that comment from the restaurant. for a GenericRelation, .remove()
    actually DELETES the comment row from the database — because content_type
    and object_id can't be null, there's no way to just "unlink" it
    """
    # restaurants.comments.remove(last_comments)

    comments=CommentModel.objects.filter(restaurant__restaurant_type='CH')
    print(comments)
    
