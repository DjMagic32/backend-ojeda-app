import graphene

from store.graphql.schema import Query as StoreQuery, Mutation as StoreMutation


class Query(StoreQuery, graphene.ObjectType):
    pass


class Mutation(StoreMutation, graphene.ObjectType):
    pass


schema = graphene.Schema(query=Query, mutation=Mutation, auto_camelcase=False)
