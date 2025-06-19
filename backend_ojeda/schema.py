import graphene
import store.schema

class Query(store.schema.Query, graphene.ObjectType):
    # This class will inherit from store.schema.Query
    # and any other app query classes if you have multiple apps.
    # Additional project-wide queries can be added here.
    pass

class Mutation(store.schema.Mutation, graphene.ObjectType):
    # This class will inherit from store.schema.Mutation
    # and any other app mutation classes if you have multiple apps.
    # Additional project-wide mutations can be added here.
    pass

schema = graphene.Schema(query=Query, mutation=Mutation)
