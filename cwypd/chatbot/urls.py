from django.urls import path
from . import views

urlpatterns = [
    # Conversations URLs
    path('ask/', views.ChatbotConversationView.as_view(), name='ask_question'),
    path('conversations/', views.ConversationListCreateView.as_view(), name='conversation-list-create'),
    path('conversations/<uuid:pk>/', views.ConversationDetailView.as_view(), name='conversation-detail'),
    path('conversations/<uuid:pk>/favourite/', views.ConversationFavouriteView.as_view(), name='conversation-favourite'),
    path('conversations/<uuid:pk>/archive/', views.ConversationArchiveView.as_view(), name='conversation-archive'),
    path('conversations/<uuid:pk>/delete/', views.ConversationDeleteView.as_view(), name='conversation-delete'),
    path('conversations/<uuid:conversation_id>/title/', views.ConversationRetrieveUpdateView.as_view(), name='conversation-title'),
    # Messages URLs
    path('messages/', views.MessageListCreateView.as_view(), name='message-list-create'),
    path('messages/<uuid:pk>/', views.MessageDetailView.as_view(), name='message-detail'),
    # URL for creating a message in a conversation
    path('conversation/<uuid:conversation_id>/create-message/', views.MessageCreateView.as_view(), name='create-message-in-conversation'),
     # URL for listing messages in a conversation
    path('conversation/<uuid:conversation_id>/list-messages/', views.MessageListView.as_view(), name='list-messages-in-conversation'),
    # User Questions URLs
    path('user-questions/', views.UserQuestionListCreateView.as_view(), name='user-question-list-create'),
    path('user-questions/<uuid:pk>/', views.UserQuestionDetailView.as_view(), name='user-question-detail'),
    # Chatbot Responses URLs
    path('chatbot-responses/', views.ChatbotResponseListCreateView.as_view(), name='chatbot-response-list-create'),
    path('chatbot-responses/<uuid:pk>/', views.ChatbotResponseDetailView.as_view(), name='chatbot-response-detail'),

]