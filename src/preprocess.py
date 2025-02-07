from music21 import *
from mido import *
from tqdm import tqdm
import os
from fractions import Fraction


def normalize_bpm_and_beat_size(midi_data, correct_bpm=120):
    norm_tracks = []

    for track in midi_data.tracks:
        changed_track = MidiTrack()
        scale_factor = 1.0

        for elem in track:
            if elem.type == 'set_tempo':
                elem.tempo = bpm2tempo(correct_bpm)
            elif elem.type == 'time_signature':
                start_numerator = elem.numerator
                start_denominator = elem.denominator

                scale_factor = (4 / start_denominator) * start_numerator
                elem = MetaMessage('time_signature', numerator=4, denominator=4, clocks_per_click=24, notated_32nd_notes_per_beat=8)

            if elem.time > 0:
                elem.time = int(elem.time * scale_factor)
            changed_track.append(elem)

        norm_tracks.append(changed_track)

    norm_midi = MidiFile()
    norm_midi.ticks_per_beat = midi_data.ticks_per_beat

    total_time = max(sum(elem.time for elem in track) for track in norm_tracks)
    measure_time = midi_data.ticks_per_beat * 4

    if len(norm_tracks) < 3:
        print(1)
        left_hand_track = MidiTrack()
        for _ in range(total_time // measure_time):
            left_hand_track.append(Message('note_on', note=0, velocity=0, time=measure_time))
        norm_midi.tracks.append(left_hand_track)

    for track in norm_tracks:
        norm_midi.tracks.append(track)

    return norm_midi



files_path = '../data/midi'
output_path = '../data/processed'
environment.set('musicxmlPath', 'C:/Program Files/MuseScore 4/bin/MuseScore4.exe')

count = 0
for music_file in tqdm(os.listdir(files_path)):
    music_path = os.path.join(files_path, music_file)
    if os.path.getsize(music_path) == 0:
        print(f"{music_path} - пустой")
        continue

    count += 1
    if count > 6:
        break
    if count == 1:
        continue
    """midi_data = converter.parse(music_path)
    midi_data.show()
    print(music_path)
    .save(os.path.join(output_path, music_file))"""

    midi_data = MidiFile(music_path)
    midi_data = normalize_bpm_and_beat_size(midi_data)
    midi_data.save(os.path.join(output_path, music_file))

    m = converter.parse(os.path.join(output_path, music_file))
    m.show()