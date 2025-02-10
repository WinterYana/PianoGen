from music21 import *
import copy
from tqdm import tqdm
import os
import numpy as np


def process_midi(midi_data, segment_size=8, bpm=120, time_signature="4/4", measure_length=4):
    parts = midi_data.parts
    all_notes = [list(part.flatten().notesAndRests) for part in parts]
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


def extract_notes_from_segment(segment, time_step=1/12, segment_length=32, max_notes=6):
    num_time_steps = int(segment_length / time_step)
    data = [[] for _ in range(num_time_steps)]

    for i, part in enumerate(segment.parts):
        hand = 1 if i == 0 else 0
        for elem in part.flatten().notesAndRests:
            start_step = round(elem.offset / time_step)
            end_step = min(start_step + round(elem.quarterLength / time_step), num_time_steps)

            if isinstance(elem, note.Note):
                note_info = [elem.pitch.midi, elem.offset, int(elem.volume.velocity) if elem.volume.velocity else 64, hand]
                for step in range(start_step, min(end_step, num_time_steps)):
                    data[step].append(note_info)
            elif isinstance(elem, chord.Chord):
                for pitch in elem.pitches:
                    note_info = [pitch.midi, elem.offset, int(elem.volume.velocity) if elem.volume.velocity else 64, hand]
                    for step in range(start_step, min(end_step, num_time_steps)):
                        data[step].append(note_info)
            elif isinstance(elem, note.Rest):  # Пауза
                note_info = [-1, elem.offset, 0, hand]
                for step in range(start_step, min(end_step, num_time_steps)):
                    data[step].append(note_info)

    for step in range(num_time_steps):
        data[step] = data[step][:max_notes]
        while len(data[step]) < max_notes:
            data[step].append([-1, step * time_step, 0, 0])
    #convert_to_midi(data)
    return data


def prepare_lstm_data(data, sequence_length=64, duration_steps=384, segment_length=32):
    sequences = []
    next_steps = []

    segment_data = np.array(data, dtype=np.float32)
    for i in range(len(segment_data) - sequence_length):
        sequences.append(segment_data[i:i + sequence_length])
        next_steps.append(segment_data[i + sequence_length])

    X = np.array(sequences)
    y = np.array(next_steps)

    X[..., 0] /= 127  # Нормализация MIDI-ноты (0-127 → 0-1)
    X[..., 1] /= segment_length  # Нормализация offset (0 - 32 → 0 - 1)
    X[..., 2] /= duration_steps  # Нормализация длительности (1-384 → 0-1)
    X[..., 3] /= 127  # Нормализация velocity (0-127 → 0-1)

    y[..., 0] /= 127
    y[..., 1] /= segment_length
    y[..., 2] /= duration_steps
    y[..., 3] /= 127
    return X, y


count = 0
files_path = '../data/midi'
output_path = '../data/processed'
environment.set('musicxmlPath', 'C:/Program Files/MuseScore 4/bin/MuseScore4.exe')

all_X = []
all_y = []
for music_file in tqdm(os.listdir(files_path)):
    music_path = os.path.join(files_path, music_file)
    if os.path.getsize(music_path) == 0:
        print(f"{music_path} - пустой")
        continue
    midi_data = converter.parse(music_path)
    if len(midi_data.parts) != 2:
        continue
    segments = process_midi(midi_data)
    for segment in segments:
        segment_data = extract_notes_from_segment(segment)
        X, y = prepare_lstm_data(segment_data)
        all_X.append(X)
        all_y.append(y)

all_X = np.concatenate(all_X, axis=0)
all_y = np.concatenate(all_y, axis=0)
np.save(os.path.join(output_path, 'all_X.npy'), all_X)
np.save(os.path.join(output_path, 'all_y.npy'), all_y)
