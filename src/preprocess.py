from music21 import *
from mido import *
from tqdm import tqdm
import os
import math


def normalize_bpm_and_bar_size(midi_data, correct_bpm=120):
    normalized_midi = stream.Score()

    for part in midi_data.parts:
        norm_part = stream.Part()
        old_tempos = list(part.flatten().getElementsByClass(tempo.MetronomeMark))
        old_time_signatures = list(part.flatten().getElementsByClass(meter.TimeSignature))

        for event in old_tempos:
            part.remove(event)
        for event in old_time_signatures:
            part.remove(event)

        new_tempo = tempo.MetronomeMark(number=correct_bpm)
        new_time_signature = meter.TimeSignature('4/4')
        norm_part.append(new_time_signature)
        norm_part.append(new_tempo)

        events_by_offset = {}  # Чтобы сохранить наложение нот
        for elem in part.flatten():
            if isinstance(elem, (tempo.MetronomeMark, meter.TimeSignature)):
                continue
            if elem.offset not in events_by_offset:
                events_by_offset[elem.offset] = []
            events_by_offset[elem.offset].append(elem)

        for offset in sorted(events_by_offset.keys()):
            chord_notes = []  # Список нот, которые должны играться одновременно
            for elem in events_by_offset[offset]:
                if isinstance(elem, note.Note) and elem.tie:
                    prev_tie = elem.tie
                    new_note = elem.__deepcopy__()
                    new_note.tie = prev_tie
                    chord_notes.append(new_note)
                elif isinstance(elem, chord.Chord):
                    chord_notes.append(elem)
                else:
                    norm_part.insert(offset, elem)

            if len(chord_notes) > 1:
                combined_chord = chord.Chord(chord_notes)
                norm_part.insert(offset, combined_chord)
            else:
                for note_elem in chord_notes:
                    norm_part.insert(offset, note_elem)

        normalized_midi.append(norm_part)

    midi_file = midi.translate.music21ObjectToMidiFile(normalized_midi)
    normalized_midi.write('midi', fp=os.path.join(output_path, music_file))
    #normalized_midi.show()
    m = converter.parse(os.path.join(output_path, music_file))
    m.show()
    return midi_file


def split_by_segments(midi_data, segment_measures=8):
    segments = []


files_path = '../data/midi'
output_path = '../data/processed'
environment.set('musicxmlPath', 'C:/Program Files/MuseScore 4/bin/MuseScore4.exe')

count = 0
for music_file in tqdm(os.listdir(files_path)):
    music_path = os.path.join(files_path, music_file)
    if os.path.getsize(music_path) == 0:
        print(f"{music_path} - пустой")
        continue
    if count < 3:
        count += 1
        continue

    midi_data = converter.parse(music_path)
    midi_data.show()
    """print(music_path)
    .save(os.path.join(output_path, music_file))"""
    normalize_bpm_and_bar_size(midi_data)

    #split_by_bars(midi_data)
    #midi_data.save(os.path.join(output_path, music_file))

    #m = converter.parse(os.path.join(output_path, music_file))

    #m.show()
    #break