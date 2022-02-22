#!/usr/bin/python3

from numpy import array
from pykicad.pcb import *
from pykicad.module import *

import argparse
import math
import numpy as np

MIN_THICKNESS = 2.4

# R_72_V10
# python3 spiral_pcb.py -i 25 -o 30.5 -r -p 8 -l 10 -s 200 -out R72V10 -vio -0.09 -voo 0.07

# GL40
# python3 spiral_pcb.py -c 22 -t 3.8 -p 8 -l 4 -s 200 -out gl40 -vio -0.09 -voo 0.07

# GL60 ID: 74.42mm  x OD: 90.84mm
# python3 spiral_pcb.py -l 12 -i 75 -t 6 -s 200 -out gl60 -voo -0.05 

# GL80 ID: 92.49mm x OD: 108.8mm
# python3 spiral_pcb.py -l 12 -i 93 -t 6 -s 200 -out gl80 -voo -0.05


def point_from_radius(angle, radius, center_offset_x, center_offset_y):
    y_value = math.sin(angle) * radius + center_offset_x
    x_value = math.cos(angle) * radius + center_offset_y
    return [x_value, y_value]

def calculate_point(idx, steps, inside_radius, width, loopnum, loop_angle, phasenum, phase_angle, angle_offset, center_offset_x, center_offset_y):
    outside_radius = inside_radius + width
    electrical_angle = (idx/steps)*math.pi*2
    a = 0.5 * (outside_radius**2 - inside_radius**2)
    b = 0.5 * (outside_radius**2 + inside_radius**2)
    radius = math.sqrt(a * math.sin(electrical_angle) + b)
    mechanical_angle = loop_angle*(idx/steps)+loopnum*loop_angle+phasenum*phase_angle + angle_offset
    return point_from_radius(mechanical_angle, radius, center_offset_x, center_offset_y)

parser = argparse.ArgumentParser(description='Generate a Kicad PCB layout for Renesas IPS2200 Inductive Encoders.')
parser.add_argument('--inner', '-i', type=float,  help='Inner Diameter (or Radius) of the coil')
parser.add_argument('--outer', '-o', type=float,  help='Outer Diameter (or Radius) of the coil')
parser.add_argument('--center', '-c', type=float,  help='Centerline Diameter (or Radius) of the coil')
parser.add_argument('--thickness', '-t', type=float,  help='Radial thickness of the coil')

parser.add_argument('--tx-loops',  '-txl', type=int, default=3, help='Transmission loop count')
parser.add_argument('--tx-loop-offset', '-txlo', type=float, default=0.6, help='Transmission loop offset in mm')
parser.add_argument('--tx-offset', '-txo', type=float, default=0.6, help='Transmission loop offset in mm')
parser.add_argument('--tx-angle', '-txa', type=float, default=(-math.pi/20), help='Transmission angle offset in radians')

parser.add_argument('--radius', '-r', action='store_const', const=True)

parser.add_argument('--phases', '-p', type=int,  default=8, help='The phase count')
parser.add_argument('--loops', '-l', type=int,  default=10, help='The loop count')
parser.add_argument('--steps', '-s', type=int,  default=200, help='The step count')

parser.add_argument('--output', '-out', default='project', help='The base filename to create')

parser.add_argument('--vinner-offset', '-vio', type=float, default=0.0, help='Inner Via Ring Offset (mm)')
parser.add_argument('--vouter-offset', '-voo', type=float, default=0.0, help='Outer Via Ring Offset (mm)')

args = parser.parse_args()

center_offset_x = 100
center_offset_y = 100

inside_radius = 0
outside_radius = 0

def get_shell_value(value, is_radius):
    if (is_radius):
        return value
    else:
        return value / 2

if (args.inner != None):
    inside_radius = get_shell_value(args.inner, args.radius)
    if (args.outer != None):
        outside_radius = get_shell_value(args.outer, args.radius)
    elif (args.thickness != None):
        outside_radius = inside_radius + args.thickness
    else:
        print('ERROR: Must provide either --outer or --thickness with --inner')
        parser.print_usage()
        exit(1)
elif (args.outer != None):
    outside_radius = get_shell_value(args.outer, args.radius)
    if (args.thickness != None):
        inside_radius = outside_radius - args.thickness
    else:
        print('ERROR: Must provide either --inner or --thickness with --outer')
        parser.print_usage()
        exit(1)
elif (args.center != None):
    if (args.thickness == None):
        print('ERROR: Must provide --thickness with --center')
        parser.print_usage()
        exit(1)
    inside_radius = (args.center / 2) - (args.thickness / 2)
    outside_radius = (args.center / 2) + (args.thickness / 2)

if (inside_radius >= (outside_radius - MIN_THICKNESS)):
    print('ERROR: --inner must be smaller than --outer minus minimum thickness (5mm diameter)')
    parser.print_usage()
    exit(1)

# radial_thickness = 10
radial_thickness = 5.5

width = outside_radius-inside_radius

# Original / Default values
# phases = 8
# loops = 10
# steps = 34

# GL40 (small)
# phases = 8
# loops = 6
# steps = 34

phases = args.phases
loops = args.loops
steps = args.steps

inner_ring_via_offset = args.vinner_offset
outer_ring_via_offset = args.vouter_offset

print('Creating coil with:')
print('Inside Diameter:', inside_radius * 2)
print('Outside Diameter:', outside_radius * 2)
print('Phases:', phases)
print('Loops:', loops)
print('Steps:', steps)


loop_angle = 2*math.pi/loops
phase_angle = loop_angle/phases
angle_offset = 0-phase_angle/2.5 - phase_angle

x_values = []
y_values = []

red = [255,0,0]
green = [0,255,0]
blue = [0,0,255]
purple = [255,0,255]

colors = [red,green,blue,purple]
point_colors = []

phase_values = [[],[],[],[]]

tx, rx1, rx2, rx3, rx4, rx5, rx6, rx7, rx8 = Net('TX'), Net('1'), Net('2'), Net('3'), Net('4'), Net('5'), Net('6'), Net('7'), Net('8')

# nets=[rx1, rx2, rx3, rx4, rx5, rx6, rx7, rx8]
# nets=[rx1, rx1, rx2, rx2, rx1, rx1, rx2, rx2]
nets=[rx2, rx2, rx1, rx1, rx2, rx2, rx1, rx1]
# nets=[rx5, rx6, rx6, rx8, rx1, rx2, rx3, rx4]

segments = []

phase_layers = ['F.Cu', 'Inner1.Cu', 'B.Cu']

special_via_point_1 = []
special_via_point_2 = []

via_list = []
last_point = [None, None, None, None, None, None, None, None]
exit_loop = False
for loopnum in range(loops):
    for phasenum in range(phases):
        skip_next_segment=False
        for idx in range(steps+1):
            if exit_loop:
                break

            if idx == steps and loopnum!=loops-1:
                # The extra step on the last loop closes a gap created
                # because last_point was none for the very first point.
                continue


            # factor = (math.sin(idx/steps*math.pi*2) + 1)/2
            # angle = loop_angle*(idx/steps)+loopnum*loop_angle+phasenum*phase_angle + angle_offset
            # radial_point_distance = inside_radius + factor * width
            # y_value = math.sin(angle) * radial_point_distance + center_offset_x
            # x_value = math.cos(angle) * radial_point_distance + center_offset_y
            current_point = calculate_point(idx, steps, inside_radius, width, loopnum, loop_angle, phasenum, phase_angle, angle_offset, center_offset_x, center_offset_y)
            bottom_layer = True
            if skip_next_segment == True:
                skip_current_segment=True
                skip_next_segment = False
            else:
                skip_current_segment=False

            if last_point[phasenum]:
                if idx<=steps/4:
                    bottom_layer = True
                if idx==int(steps/4) or idx==int(3*steps/4):
                    if loopnum == int(loops-1) and phasenum==4 and idx==int(steps/4):
                            tmp_pt=calculate_point(idx, steps, inside_radius+4, width, loopnum, loop_angle, phasenum, phase_angle, angle_offset, center_offset_x, center_offset_y)
                            segments.append(Segment(start=current_point, end=tmp_pt, layer='B.Cu', net=nets[phasenum].code))
                            skip_next_segment=True
                    else:
                        if idx==int(steps/4):
                            tmp_radius = inside_radius + outer_ring_via_offset
                        else:
                            tmp_radius = inside_radius + inner_ring_via_offset
                        tmp_pt=calculate_point(idx, steps, tmp_radius, width, loopnum, loop_angle, phasenum, phase_angle, angle_offset, center_offset_x, center_offset_y)
                        via_list.append(Via(at=tmp_pt, size=.5, drill=.3, net=nets[phasenum].code))
                        # print('aye:', tmp_pt)

                if loopnum == int(loops-1) and phasenum==4 and idx==int(steps/4)+1:
                        tmp_pt=calculate_point(idx-0.5, steps, inside_radius-0.75, width, loopnum, loop_angle, phasenum, phase_angle, angle_offset, center_offset_x, center_offset_y)
                        segments.append(Segment(start=current_point, end=tmp_pt, layer='F.Cu', net=nets[phasenum].code))
                        via_list.append(Via(at=tmp_pt, size=.5, drill=.3, net=nets[phasenum].code))
                        special_via_point_1 = tmp_pt
                        # print('bee:', tmp_pt)
                if loopnum == int(loops-1) and phasenum==5 and idx==int(steps/4)-4:
                    segments.append(Segment(start=current_point, end=special_via_point_1, layer='B.Cu', net=nets[phasenum].code))
                    skip_next_segment=True
                if loopnum == int(loops-1) and phasenum==5 and idx==int(steps/4)-3:
                    tmp_pt1=calculate_point(idx-0.3, steps, inside_radius, width, loopnum, loop_angle, phasenum, phase_angle, angle_offset, center_offset_x, center_offset_y)
                    tmp_pt2=calculate_point(idx+0.2, steps, inside_radius+0.4, width, loopnum, loop_angle, phasenum, phase_angle, angle_offset, center_offset_x, center_offset_y)
                    tmp_pt3=calculate_point(idx-0.6, steps, inside_radius+1.6, width, loopnum, loop_angle, phasenum, phase_angle, angle_offset, center_offset_x, center_offset_y)
                    tmp_pt4=calculate_point(idx-0.6, steps, inside_radius+4, width, loopnum, loop_angle, phasenum, phase_angle, angle_offset, center_offset_x, center_offset_y)
                    segments.append(Segment(start=current_point, end=tmp_pt1, layer='B.Cu', net=nets[phasenum].code))
                    segments.append(Segment(start=tmp_pt1, end=tmp_pt2, layer='B.Cu', net=nets[phasenum].code))
                    segments.append(Segment(start=tmp_pt2, end=tmp_pt3, layer='B.Cu', net=nets[phasenum].code))
                    segments.append(Segment(start=tmp_pt3, end=tmp_pt4, layer='B.Cu', net=nets[phasenum].code))


                if idx>steps/4 and idx < 3*steps/4:
                    bottom_layer = False
                if idx>3*steps/4:
                    bottom_layer = True

                if loopnum == int(loops/2)-1 and phasenum>=phases/2:
                    if idx==int(steps/2) + int(steps / 34):
                        via_list.append(Via(at=current_point, size=.5, drill=.3, net=nets[phasenum].code))
                        # bottom_layer = not bottom_layer
                    if idx <= int(steps/2) + int(steps / 34) and idx >= int(steps/2)+1:
                        bottom_layer = not bottom_layer

                if loopnum == int(loops/2)-1 and phasenum<phases/2:
                    if idx==steps - (int(steps / 34) - 1):
                        via_list.append(Via(at=last_point[phasenum], size=.5, drill=.3, net=nets[phasenum].code))

                    if idx > steps - (int(steps / 34)):
                        bottom_layer = not bottom_layer

                if idx == 0 and loopnum == int(loops / 2) and phasenum < phases/2:
                    bottom_layer = not bottom_layer

                if loopnum == int(loops-1) and phasenum==3 and idx==int(steps/4)-4:
                    segments.append(Segment(start=current_point, end=special_via_point_1, layer='B.Cu', net=nets[phasenum].code))
                    skip_next_segment=True
                if loopnum == int(loops-1) and phasenum==2 and idx==int(steps/4):
                    via_list = via_list[:-1]
                    skip_next_segment=True
                    special_via_point_2 = current_point
                if loopnum == int(loops-1) and phasenum==2 and idx==int(steps/4)+1:
                    tmp_pt=calculate_point(idx-0.5, steps, inside_radius-0.75, width, loopnum, loop_angle, phasenum, phase_angle, angle_offset, center_offset_x, center_offset_y)
                    segments.append(Segment(start=current_point, end=tmp_pt, layer='F.Cu', net=nets[phasenum].code))
                    via_list.append(Via(at=tmp_pt, size=.5, drill=.3, net=nets[phasenum].code))
                    special_via_point_1 = tmp_pt
                if loopnum == int(loops-1) and phasenum==3 and idx==int(steps/4)-3:
                    tmp_pt1=calculate_point(idx-0.3, steps, inside_radius, width, loopnum, loop_angle, phasenum, phase_angle, angle_offset, center_offset_x, center_offset_y)
                    tmp_pt2=calculate_point(idx+0.2, steps, inside_radius+0.4, width, loopnum, loop_angle, phasenum, phase_angle, angle_offset, center_offset_x, center_offset_y)
                    tmp_pt3=calculate_point(idx-0.3, steps, inside_radius+1.2, width, loopnum, loop_angle, phasenum, phase_angle, angle_offset, center_offset_x, center_offset_y)
                    tmp_pt4=calculate_point(idx-1, steps, inside_radius, width, loopnum, loop_angle, phasenum, phase_angle, angle_offset, center_offset_x, center_offset_y)
                    segments.append(Segment(start=current_point, end=tmp_pt1, layer='B.Cu', net=nets[phasenum].code))
                    segments.append(Segment(start=tmp_pt1, end=tmp_pt2, layer='B.Cu', net=nets[phasenum].code))
                    segments.append(Segment(start=tmp_pt2, end=tmp_pt3, layer='B.Cu', net=nets[phasenum].code))
                    segments.append(Segment(start=tmp_pt3, end=special_via_point_2, layer='B.Cu', net=nets[phasenum].code))

                if loopnum == int(loops-1) and phasenum==3 and idx==int(steps/4)-1:
                    tmp_pt1=calculate_point(idx+0.3, steps, inside_radius, width, loopnum, loop_angle, phasenum, phase_angle, angle_offset, center_offset_x, center_offset_y)
                    tmp_pt2=calculate_point(idx+0.3, steps, inside_radius+4, width, loopnum, loop_angle, phasenum, phase_angle, angle_offset, center_offset_x, center_offset_y)
                    segments.append(Segment(start=current_point, end=tmp_pt1, layer='B.Cu', net=nets[phasenum].code))
                    segments.append(Segment(start=tmp_pt1, end=tmp_pt2, layer='B.Cu', net=nets[phasenum].code))
                    skip_next_segment=True

                if loopnum == int(loops-1) and phasenum==3 and idx==int(steps/4):
                    tmp_pt1=calculate_point(idx, steps, inside_radius+4, width, loopnum, loop_angle, phasenum, phase_angle, angle_offset, center_offset_x, center_offset_y)
                    segments.append(Segment(start=current_point, end=tmp_pt1, layer='B.Cu', net=nets[phasenum].code))

                layer = 'B.Cu' if bottom_layer else 'F.Cu'
                if not skip_current_segment:
                    segments.append(Segment(start=last_point[phasenum], end=current_point, layer=layer, net=nets[phasenum].code))

            last_point[phasenum] = current_point



tx_steps = 300
tx_loops = args.tx_loops
loop_offset_mm = args.tx_loop_offset
tx_offset_mm = args.tx_offset
last_point = None
tx_angle_offset = args.tx_angle
tx_extra_tail_mm = 2
tail_end_pt = None

for loopnum in range(tx_loops+1):
    for stepnum in range(tx_steps):
        radius = loopnum * loop_offset_mm + outside_radius + tx_offset_mm
        angle = stepnum/tx_steps * math.pi * 2 + tx_angle_offset
        current_point = point_from_radius(angle, radius, center_offset_x, center_offset_y)

        if stepnum == 0 and loopnum==0:
            via_angle = (stepnum+0.15)/tx_steps * math.pi * 2 + tx_angle_offset
            via_point = point_from_radius(via_angle, radius, center_offset_x, center_offset_y)
            via_list.append(Via(at=via_point, size=.5, drill=.3, net=tx.code))
            tmp_radius = radius + tx_loops*loop_offset_mm + tx_extra_tail_mm
            tail_end_pt = point_from_radius(angle, tmp_radius, center_offset_x, center_offset_y)
            segments.append(Segment(start=current_point, end=tail_end_pt, layer='B.Cu', net=tx.code))

        if stepnum == 0 and last_point:
            radius_tmp1 = (loopnum-1) * loop_offset_mm + outside_radius + tx_offset_mm
            radius_tmp2 = radius - loop_offset_mm/3
            angle_tmp1 = (loopnum * -0.08-0.75)/tx_steps * math.pi * 2 + tx_angle_offset
            angle_tmp2 = (loopnum * -0.08-0.3)/tx_steps * math.pi * 2 + tx_angle_offset
            tmp_point1 = point_from_radius(angle_tmp1, radius_tmp1, center_offset_x, center_offset_y)
            tmp_point2 = point_from_radius(angle_tmp2, radius_tmp2, center_offset_x, center_offset_y)
            segments.append(Segment(start=last_point, end=tmp_point1, layer='F.Cu', net=tx.code))
            segments.append(Segment(start=tmp_point1, end=tmp_point2, layer='F.Cu', net=tx.code))
            last_point = tmp_point2

        if last_point:
            # print(current_point)
            segments.append(Segment(start=last_point, end=current_point, layer='F.Cu', net=tx.code))
        last_point = current_point
        if loopnum == tx_loops:
            segments.append(Segment(start=current_point, end=tail_end_pt, layer='F.Cu', net=tx.code))
            break


coords = [(0, 0), (10, 0), (10, 10), (0, 10)]
gndplane_top = Zone(net_name='GND', layer='F.Cu', polygon=coords, clearance=0.3)

layers = [
Layer('F.Cu'),
# Layer('Inner1.Cu'),
# Layer('Inner2.Cu'),
Layer('B.Cu'),
Layer('Edge.Cuts', type='user')
]

for layer in ['Mask', 'Paste', 'SilkS', 'CrtYd', 'Fab']:
    for side in ['B', 'F']:
        layers.append(Layer('%s.%s' % (side, layer), type='user'))
        nc1 = NetClass('default', trace_width=1, nets=['TX', 'RX1', 'RX2'])

# print(via_list)

# Create PCB
pcb = Pcb()
pcb.title = 'A title'
pcb.comment1 = 'Comment 1'
pcb.page_type = [200, 200]
pcb.num_nets = 3
pcb.setup = Setup(grid_origin=[10, 10])
pcb.layers = layers
# pcb.modules += [r1, r2]
pcb.net_classes += [nc1]
pcb.nets += [rx1, rx2, tx]
pcb.segments += segments
pcb.vias += via_list
# pcb.zones += [gndplane_top]

pcb.to_file(args.output)

print('Creation Completed at:', args.output + '.kicad_pcb')

#export KISYSMOD=/usr/share/kicad-nightly/footprints/
