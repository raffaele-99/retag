# Agent

> This file describes the project and it's goals, with the intention that it is read by coding agents to assist in achieving the project's goals.

## Project overview

This project is called `retagger`. It is a tool to normalise metadata for .mp3 files.

## What problem is this project trying to solve?

I am transitioning off of streaming services to simplify my decision-making and save money. I have various old iPods that I have been using to listen to music, but the music that I download from Deemix is stored in a format that does not mix well with MP3 players.

Among other things, the most pressing issue is that the `Artist` field is formatted as "Main/Feat", which is not a standard format and is not supported by most MP3 players - for example, the song "Clarity (ft. Foxes)" by Zedd is downloaded from Deemix as "Clarity" (title) and "Zedd/Foxes" (artists), which would then create a new artist listing on an iPod for `Zedd/Foxes`.

This project aims to provide a simple way to fix this issue by accepting .mp3 files (either directly or a directory containing them) and normalizing the metadata to a standard format. So, for example, the song "Clarity" (title) "Zedd/Foxes" (artists) would be changed to "Clarity (ft. Foxes)" (title) and "Zedd" (artist), with the `albumartist` field set to "Zedd" as well.

# Project goal

- **The goal of this project is to create a simple, user-friendly tool that can be used to normalise metadata for .mp3 files. It should be easy to use and require no installation or setup.**
- A simple GUI interface would be ideal, as it would enable the ability for users to drag and drop files or folders.
- No dependency installation should be required. The tool should be self-contained and require no additional packages; perhaps these can be bundled or something (I am not sure if this is possible).

## Current state

- The current state of the project is a fully-functional python script that accepts a directory and supports a dry-run mode to verify the changes before execution.

## Issues

- It is not particularly intuitive to have to open a terminal and run a script every time I download more music. I would like to make it easier for my friends and family to switch to downloading MP3s, and telling them to download python + set up their terminal is not really user-friendly.

## Logic checks

- There are some logic checks performed to handle certain edge cases. For example, if the artist field is empty, or if the artist field does not contain the delimiter, the file is skipped. Additionally, the `albumartist` is used to determine who the main artist is when multiple names appear in the artist field.

