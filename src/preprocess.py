from music21 import *
import copy
from tqdm import tqdm
import os
import math


def process_midi(midi_data, segment_size=8, bpm=120, time_signature="4/4", measure_length=4):
    parts = midi_data.parts
    all_notes = [list(part.flat.notesAndRests) for part in parts]
    segment_length = segment_size * measure_length

    segments = []
    for i, part_notes in enumerate(all_notes):
        for note_now in part_notes:
            note_length = note_now.duration.quarterLength
            note_offset = note_now.offset

            while note_length > 0:
                segment_index = int(note_offset // segment_length)
                while segment_index >= len(segments):
                    new_segment = stream.Score()
                    new_segment.insert(0, tempo.MetronomeMark(number=bpm))
                    new_segment.insert(0, meter.TimeSignature(time_signature))
                    for _ in range(len(parts)):
                        new_segment.append(stream.Part())
                    segments.append(new_segment)

                current_part = segments[segment_index].parts[i]
                segment_offset = note_offset % segment_length
                free_time = segment_length - segment_offset

                if note_length <= free_time:
                    full_copy = copy.deepcopy(note_now)
                    full_copy.offset = segment_offset
                    current_part.insert(full_copy)
                    note_length = 0
                else:
                    first_part = copy.deepcopy(note_now)
                    second_part = copy.deepcopy(note_now)
                    first_part.duration = duration.Duration(free_time)
                    second_part.duration = duration.Duration(note_length - free_time)
                    first_part.offset = segment_offset
                    current_part.insert(first_part)

                    note_now = second_part
                    note_offset += free_time
                    note_length -= free_time

    last_segment = segments[-1]
    last_segment_quarters = last_segment.duration.quarterLength

    if last_segment_quarters < (segment_length / 2):
        segments.pop()
    else:
        for part in last_segment.parts:
            free_time = segment_length - last_segment_quarters
            if last_segment_quarters % measure_length != 0:
                rest_time = measure_length - (last_segment_quarters % measure_length)
                rest = note.Rest()
                rest.duration = duration.Duration(rest_time)

                part.append(rest)
                free_time -= rest_time
            while free_time > 0:
                rest = note.Rest()
                rest.duration = duration.Duration(measure_length)

                part.append(rest)
                free_time -= measure_length

    return segments


files_path = '../data/midi'
output_path = '../data/processed'
environment.set('musicxmlPath', 'C:/Program Files/MuseScore 4/bin/MuseScore4.exe')

count = 0
for music_file in tqdm(os.listdir(files_path)):
    music_path = os.path.join(files_path, music_file)
    if os.path.getsize(music_path) == 0:
        print(f"{music_path} - пустой")
        continue

    midi_data = converter.parse(music_path)
    if len(midi_data.parts) != 2:
        continue
    segments = process_midi(midi_data)
