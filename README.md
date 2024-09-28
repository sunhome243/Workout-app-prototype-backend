# Workout App API Documentation

## Table of Contents
1. [Introduction](#introduction)
2. [Architecture](#architecture)
3. [Authentication](#authentication)
4. [User Service API](#user-service-api)
5. [Workout Service API](#workout-service-api)
6. [Error Handling](#error-handling)
7. [Data Models](#data-models)
8. [Contact](#contact)

## Introduction

This document provides a comprehensive overview of the Workout App API. Our application is designed to help users manage their workout routines, track progress, and interact with personal trainers. The API is split into two main services: User Service and Workout Service.

## Architecture

Our Workout App uses a microservices architecture, with two main services communicating via REST APIs. Here's a high-level overview of our system architecture:

```
┌─────────────────┐         ┌─────────────────┐
│                 │         │                 │
│   User Service  │◀───────▶│ Workout Service │
│   (Port 8000)   │         │   (Port 8001)   │
│                 │         │                 │
└────────┬────────┘         └────────┬────────┘
         │                           │
         │                           │
         │        ┌─────────────┐    │
         │        │             │    │
         └───────▶│  PostgreSQL │◀───┘
                  │  Database   │
                  │             │
                  └─────────────┘
         │                           │
         │        ┌─────────────┐    │
         │        │             │    │
         └───────▶│  Firebase   │◀───┘
                  │    Auth     │
                  │             │
                  └─────────────┘
```

Both services use PostgreSQL for data storage and Firebase Auth for authentication.

## Authentication

All endpoints require authentication using Firebase Auth. Include the Firebase ID token in the Authorization header of your requests:

```
Authorization: Bearer <your-firebase-id-token>
```

## User Service API

Base URL: `http://localhost:8000`

### User Management

#### Create User
- **POST** `/api/users/`
- Creates a new user (member or trainer)
- Body: `UserCreate` schema

#### Get Current Member
- **GET** `/api/members/me/`
- Retrieves the current member's profile

#### Get Current Trainer
- **GET** `/api/trainers/me/`
- Retrieves the current trainer's profile

#### Update Member Profile
- **PATCH** `/api/members/me`
- Updates the current member's profile
- Body: `MemberUpdate` schema

### Trainer-Member Relationships

#### Request Trainer-Member Mapping
- **POST** `/api/trainer-member-mapping/request`
- Initiates a request for trainer-member relationship
- Body: `CreateTrainerMemberMapping` schema

#### Update Trainer-Member Mapping Status
- **PATCH** `/api/trainer-member-mapping/{mapping_id}/status`
- Updates the status of a trainer-member mapping
- Body: `TrainerMemberMappingUpdate` schema

#### Get My Mappings
- **GET** `/api/my-mappings/`
- Retrieves all mappings for the current user

#### Remove Specific Mapping
- **DELETE** `/api/trainer-member-mapping/{other_uid}`
- Removes a specific trainer-member mapping

### FCM Token Management

#### Add FCM Token
- **POST** `/api/fcm-token`
- Adds a new FCM token for the user

#### Remove FCM Token
- **DELETE** `/api/fcm-token`
- Removes an FCM token for the user

#### Refresh FCM Token
- **PUT** `/api/fcm-token`
- Refreshes an FCM token for the user

## Workout Service API

Base URL: `http://localhost:8001`

### Session Management

#### Create Session
- **POST** `/api/create_session`
- Creates a new workout session
- Query Parameters: `session_type_id`, `quest_id`, `member_uid`

#### Save Session
- **POST** `/api/save_session`
- Saves a completed workout session
- Body: `SessionSave` schema

#### Get Session Detail
- **GET** `/api/session/{session_id}`
- Retrieves details of a specific session

#### Get Sessions
- **GET** `/api/sessions`
- Retrieves all sessions for the current user

### Quest Management

#### Create Quest
- **POST** `/api/create_quest`
- Creates a new quest (trainer only)
- Body: `QuestCreate` schema

#### Get Quests
- **GET** `/api/quests`
- Retrieves all quests for the current user

#### Get Quests for Member
- **GET** `/api/quests/{member_uid}`
- Retrieves all quests for a specific member (trainer only)

#### Delete Quest
- **DELETE** `/api/quests/{quest_id}`
- Deletes a specific quest

### Workout Information

#### Search Workouts
- **GET** `/api/search-workouts`
- Searches for workouts by name
- Query Parameter: `workout_name`

#### Get Workouts by Part
- **GET** `/api/workouts-by-part`
- Retrieves workouts grouped by body part
- Query Parameter: `workout_part_id` (optional)

#### Get Workout Records
- **GET** `/api/workout-records/{workout_key}`
- Retrieves workout records for a specific workout

#### Get Workout Name
- **GET** `/api/workout-name/{workout_key}`
- Retrieves the name of a specific workout

### Analytics

#### Get Session Counts
- **GET** `/api/session_counts/{member_uid}`
- Retrieves session counts for a member within a date range
- Query Parameters: `start_date`, `end_date`

#### Get Last Session Update
- **GET** `/api/last-session-update/{uid}`
- Retrieves the timestamp of the last session update for a user

#### Get Trainer Assigned Members' Sessions
- **GET** `/api/trainer/assigned-members-sessions`
- Retrieves sessions for all members assigned to the trainer (trainer only)

## Error Handling

The API uses standard HTTP status codes to indicate the success or failure of requests. In case of an error, the response will include a JSON object with a `detail` field explaining the error.

## Data Models

For detailed information about request and response data models, please refer to the `schemas.py` files in each service.

## Notes

- Ensure you're using Firebase Auth for authentication and include the Firebase ID token in all requests.
- Some endpoints are role-specific (e.g., trainer-only endpoints). Ensure you're using the correct account type when accessing these endpoints.
- All dates and times are in ISO 8601 format and in UTC timezone unless specified otherwise.

## Contact

If you have any questions, issues, or need further clarification about the API, please don't hesitate to contact our development team at dev@workoutapp.com.

We're here to help you integrate our API successfully into your applications!
