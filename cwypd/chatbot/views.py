from django.shortcuts import render
from django.shortcuts import get_object_or_404
from rest_framework import generics, status
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import LimitOffsetPagination
from django.core.exceptions import ObjectDoesNotExist
from django.contrib.auth import get_user_model
from .models import Conversation, Message
from .serializers import ConversationSerializer, MessageSerializer
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework import status
import pinecone
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.vectorstores import Pinecone
from langchain.chains import ConversationalRetrievalChain
from langchain.chains.conversation.memory import ConversationBufferMemory
from langchain.chat_models import ChatOpenAI
from rest_framework.permissions import AllowAny,IsAuthenticated
from .models import Chat, Message
from rest_framework.generics import ListCreateAPIView, RetrieveUpdateDestroyAPIView
from rest_framework import permissions
from .models import UserQuestion, ChatbotResponse
from .serializers import UserQuestionSerializer, ChatbotResponseSerializer
from rest_framework.decorators import authentication_classes
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
User = get_user_model()


class LastMessagesPagination(LimitOffsetPagination):
    """
    Pagination class for last messages.
    """
    default_limit = 10
    max_limit = 10


#List and create conversations
class ConversationListCreateView(generics.ListCreateAPIView):
    """
    List and create conversations.
    """
    serializer_class = ConversationSerializer

    def get_queryset(self):
        return Conversation.objects.filter(user=self.request.user).order_by('created_at')

    def perform_create(self, serializer):
        serializer.save(user=self.request.user)

class MessageCreate(generics.CreateAPIView):
    """
    Create a message in a conversation.
    """
    serializer_class = MessageSerializer

    def perform_create(self, serializer):
        conversation_id = self.kwargs['conversation_id']
        serializer.save(conversation_id=conversation_id, is_from_user=True)

    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

# Retrieve, update, and delete a specific conversation
class ConversationDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    Retrieve, update, and delete a specific conversation.
    """
    serializer_class = ConversationSerializer

    def get_queryset(self):
        return Conversation.objects.filter(user=self.request.user)

    def delete(self, request, *args, **kwargs):
        conversation = self.get_object()
        if conversation.user != request.user:
            return Response(status=status.HTTP_403_FORBIDDEN)
        return super().delete(request, *args, **kwargs)


# Archive a conversation
class ConversationArchiveView(APIView):
    """
    Archive a conversation.
    """

    def patch(self, request, pk):
        conversation = get_object_or_404(Conversation, id=pk, user=request.user)
        if conversation.archive:
            conversation.archive = False
            conversation.save()
            return Response({"message": "remove from archive"}, status=status.HTTP_200_OK)
        else:
            conversation.archive = True
            conversation.save()
            return Response({"message": "add to archive"}, status=status.HTTP_200_OK)


class ConversationFavouriteView(APIView):
    """
    Favourite a conversation.
    """

    def patch(self, request, pk):
        conversation = get_object_or_404(Conversation, id=pk, user=request.user)
        if conversation.favourite:
            conversation.favourite = False
            conversation.save()
            return Response({"message": "remove from favourite"}, status=status.HTTP_200_OK)
        else:
            conversation.favourite = True
            conversation.save()
            return Response({"message": "add to favourite"}, status=status.HTTP_200_OK)


# Delete a conversation
class ConversationDeleteView(APIView):
    """
    Delete a conversation.
    """

    def delete(self, request, pk):
        conversation = get_object_or_404(Conversation, id=pk, user=request.user)
        conversation.delete()
        return Response({"message": "conversation deleted"}, status=status.HTTP_200_OK)


# List messages in a conversation
class MessageListView(generics.ListAPIView):
    """
    List messages in a conversation.
    """
    serializer_class = MessageSerializer
    pagination_class = LastMessagesPagination

    def get_queryset(self):
        conversation = get_object_or_404(Conversation, id=self.kwargs['conversation_id'], user=self.request.user)
        return Message.objects.filter(conversation=conversation).select_related('conversation')


# Create a message in a conversation
class MessageCreateView(generics.CreateAPIView):
    """
    Create a message in a conversation.
    """
    serializer_class = MessageSerializer

    def perform_create(self, serializer):
        conversation = get_object_or_404(Conversation, id=self.kwargs['conversation_id'], user=self.request.user)
        serializer.save(conversation=conversation, is_from_user=True)

        # Retrieve the last 10 messages from the conversation
        messages = Message.objects.filter(conversation=conversation).order_by('-created_at')[:10][::-1]

        # Build the list of dictionaries containing the message data
        message_list = []
        for msg in messages:
            if msg.is_from_user:
                message_list.append({"role": "user", "content": msg.content})
            else:
                message_list.append({"role": "assistant", "content": msg.content})

        # Mock system prompt (you can replace this with your preferred default prompt)
        system_prompt = "You are sonic you can do anything you want."

        # Simulate a response from GPT-3 (replace this with your logic to generate a response)
        # For demonstration purposes, this just returns a simple response
        response = "This is a mock response from GPT-3."

        # You can return the response and other data as needed
        return [response, conversation.id, messages[0].id]

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        response_list = self.perform_create(serializer)
        assistant_response = response_list[0]
        conversation_id = response_list[1]
        last_user_message_id = response_list[2]

        try:
            # Store GPT response as a message
            message = Message(
                conversation_id=conversation_id,
                content=assistant_response,
                is_from_user=False,
                in_reply_to_id=last_user_message_id
            )
            message.save()

        except ObjectDoesNotExist:
            error = f"Conversation with id {conversation_id} does not exist"
            Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)
        except Exception as e:
            error_mgs = str(e)
            error = f"Failed to save GPT-3 response as a message: {error_mgs}"
            Response({"error": error}, status=status.HTTP_400_BAD_REQUEST)

        headers = self.get_success_headers(serializer.data)
        return Response({"response": assistant_response}, status=status.HTTP_200_OK, headers=headers)


class ConversationRetrieveUpdateView(generics.RetrieveUpdateAPIView):
    """
    Retrieve View to update or get the title
    """
    queryset = Conversation.objects.all()
    serializer_class = ConversationSerializer
    lookup_url_kwarg = 'conversation_id'

    def retrieve(self, request, *args, **kwargs):
        conversation = self.get_object()

        if conversation.title == "Empty":
            messages = Message.objects.filter(conversation=conversation)

            if messages.exists():
                message_list = []
                for msg in messages:
                    if msg.is_from_user:
                        message_list.append({"role": "user", "content": msg.content})
                    else:
                        message_list.append({"role": "assistant", "content": msg.content})

                # For example, here it just concatenates content from messages
                my_title = "".join(msg.content for msg in messages)[:30]
                conversation.title = my_title
                conversation.save()
                serializer = self.get_serializer(conversation)
                return Response(serializer.data)
            else:
                return Response({"message": "No messages in conversation."}, status=status.HTTP_204_NO_CONTENT)
        else:
            serializer = self.get_serializer(conversation)
            return Response(serializer.data)

class ChatbotConversationView(APIView):
      permission_classes = [IsAuthenticated]

      def post(self, request, *args, **kwargs):
            query = request.data.get('query')
            chat_history = request.data.get('chat_history', [])
            # Check if a conversation exists for the user
            conversation, created = Conversation.objects.get_or_create(user=request.user)
            if query:
                # Create a new question associated with the conversation
                question = UserQuestion.objects.create(conversation=conversation, user=request.user,question_text=query)

                payload = request.data
                query = payload.get('query')
                chat_history = payload.get('chat_history', [])

                pinecone_api_key = "16f1dbb3-8617-4c1a-baea-57899e3a8db1"
                pinecone_environment = "gcp-starter"
                pinecone_index_name = "testindex"
                openai_api_key = "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"

                pinecone.init(api_key=pinecone_api_key, environment=pinecone_environment)
                embeddings = OpenAIEmbeddings(openai_api_key=openai_api_key)

                db = Pinecone.from_existing_index(index_name=pinecone_index_name, embedding=embeddings)

                memory = ConversationBufferMemory(memory_key='chat_history', return_messages=False)

                cqa = ConversationalRetrievalChain.from_llm(
                    llm=ChatOpenAI(model="gpt-3.5-turbo",temperature=0.0, openai_api_key=openai_api_key),
                    retriever=db.as_retriever(),#gpt-4-1106-preview
                    memory=memory,
                    get_chat_history=lambda h: h
                )

                result = cqa({'question': query, 'chat_history': chat_history})
                chat_history.append((query, result['answer']))
                
                # For demonstration purposes, assume 'response_text' contains the response
                response_text = result

                # Store the response in the database
                response = ChatbotResponse.objects.create(conversation=conversation, response_text=response_text)
                # response_message = Message.objects.create(conversation=conversation, content=response_text, is_from_user=False)


                return Response({
                    'result': response_text,
                    'chat_history': chat_history  # You might want to update chat history based on response
                }, status=status.HTTP_200_OK)

            return Response({'error': 'No question provided'}, status=status.HTTP_400_BAD_REQUEST)

            

class UserQuestionListCreateView(ListCreateAPIView):
    queryset = UserQuestion.objects.all()
    serializer_class = UserQuestionSerializer
    permission_classes = [permissions.IsAuthenticated]  # Example: Only authenticated users can create questions

    def perform_create(self, serializer):
        # Custom logic before saving the new question
        serializer.save(user=self.request.user)  # Assuming UserQuestion model has a 'user' field

class UserQuestionDetailView(RetrieveUpdateDestroyAPIView):
    queryset = UserQuestion.objects.all()
    serializer_class = UserQuestionSerializer
    permission_classes = [permissions.IsAuthenticated]  # Example: Only authenticated users can view/update/delete

class ChatbotResponseListCreateView(ListCreateAPIView):
    queryset = ChatbotResponse.objects.all()
    serializer_class = ChatbotResponseSerializer
    permission_classes = [permissions.IsAuthenticated]  # Example: Only authenticated users can create responses

    def perform_create(self, serializer):
        # Custom logic before saving the new chatbot response
        serializer.save(user=self.request.user)  # Assuming ChatbotResponse model has a 'user' field

class ChatbotResponseDetailView(RetrieveUpdateDestroyAPIView):
    queryset = ChatbotResponse.objects.all()
    serializer_class = ChatbotResponseSerializer
    permission_classes = [permissions.IsAuthenticated]  # Example: Only authenticated users can view/update/delete

class MessageListCreateView(generics.ListCreateAPIView):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer

class MessageDetailView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Message.objects.all()
    serializer_class = MessageSerializer