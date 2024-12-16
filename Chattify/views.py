from django.shortcuts import render
from rest_framework.decorators import api_view
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth.models import User
from rest_framework import status
from django.contrib import auth
from .serializers import UserSerializer

# Create your views here.
@api_view(['POST'])
def register(request):
    data = request.data
    username = data.get("username")
    email = data.get("email")
    password = data.get("password")
    password2 = data.get("password2")

    try:

        if password == password2:
            if User.objects.filter(username=username).exists():
                return Response({
                    "status":"error",
                    "message":"username already exists"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            elif User.objects.filter(email=email).exists():
                return Response({
                    "status":"error",
                    "message":"Email already exists"
                }, status=status.HTTP_400_BAD_REQUEST)
            
            else:
                user = User.objects.create_user(username=username, email=email, password=password)
                user.save()

                token, _ = Token.objects.get_or_create(user=user)
                
                response =  Response({
                    "status":"success",
                    "message":"You Registered Successfully",
                    "token":token.key,
                }, status=status.HTTP_201_CREATED)

                

            return response    
            

        else:
            return Response({
                "status":"error",
                "message":"Password does not match"
            }, status=status.HTTP_400_BAD_REQUEST)
     

    except Exception as e:
        return Response({
            "status":"error",
            "message":f"Error Registering user {e}"
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)    




@api_view(['POST'])
def login(request):
    data = request.data
    username = data.get("username")
    password = data.get("password")

    if not username or not password:
        return Response({
            "status":"error",
            "message":"username and Password are required",
        }, status=status.HTTP_400_BAD_REQUEST)

    user = auth.authenticate(username=username, password=password)

    try:

        if user:
            auth.login(request, user)

            token, created = Token.objects.get_or_create(user=user)

            response = Response({
                "status":"success",
                "message":"You Loggedin Successfully",
                "token":token.key,
                "payload": {
                    "username":username,
                    "email":request.user.email
                },
            }, status=status.HTTP_200_OK)
        

            response.set_cookie(
                key='isLoggedin',            
                value=bool(True),           
                httponly=True,
                secure=True,               
                samesite='Lax',  
                path='/', 
                max_age=60 * 60 * 24 * 7 
            )

            return response
        
        else:
            return Response({
                "status":"error",
                "message":"invalid Credentials",
            }, status=status.HTTP_400_BAD_REQUEST)
        
    except Exception as e:
        return Response({
            "status":"error",
            "message":f"An Error occured {e}",
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)





@api_view(['POST'])
def logout(request):
    try:
        auth.logout(request)
        return Response({
            "status":"success",
            "message":"You Loggedout Successfully",
            
        }, status=status.HTTP_200_OK)

    except Exception as e:
        return Response({
            "status":"error",
            "message":f"An Error occured trying to log you out {e}",
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
    



@api_view(['GET'])
def get_users(request):
    user = request.user
    if not user.is_authenticated:
        return Response({
            "status": "error",
            "message": "User is not authenticated"
        }, status=status.HTTP_401_UNAUTHORIZED)

    try:
        all_users = User.objects.exclude(id=user.id)
        serializer = UserSerializer(all_users, many=True)
        return Response({
            "status":"success",
            "message":"Users retrieved successfully",
            "data":{
                "users":serializer.data
            }
        }, status=status.HTTP_200_OK)
    
    except Exception as e:
        return Response({
            "status":"error",
            "message":f"Error fetching users {e}"
        }, status=status.HTTP_400_BAD_REQUEST)
