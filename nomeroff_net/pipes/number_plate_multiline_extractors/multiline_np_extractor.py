import cv2
import numpy as np
from typing import List, Dict, Tuple

from nomeroff_net.tools import (fline,
                                distance,
                                minimum_bounding_rectangle,
                                fix_clockwise2,
                                linear_line_matrix,
                                get_y_by_matrix,
                                rotate,
                                detect_intersection,
                                find_min_x_idx,
                                reshape_points)


def normalize_multiline_rect(rect: np.ndarray, mline_boxes: List) -> np.ndarray or List:
    """
    TODO: describe function
    """
    rect = fix_clockwise2(rect)
    min_x_idx = find_min_x_idx(rect)
    rect = reshape_points(rect, min_x_idx)

    w_max, w_max_idx, options = make_mline_boxes_options(mline_boxes)
    target_angle = options[w_max_idx]['angle']
    coef_ccw = fline(rect[0], rect[3])
    angle_ccw = round(coef_ccw[2], 2)

    if abs(target_angle-angle_ccw) > 45:
        rect = reshape_points(rect, 3)
    return rect


def fix_box_angle(target_angle: float, mline_box: List, option: Dict) -> List:
    line_matrix_left = linear_line_matrix(mline_box[0], mline_box[2])
    line_matrix_right = linear_line_matrix(mline_box[1], mline_box[3])
    origin = detect_intersection(line_matrix_left, line_matrix_right)
    angle = target_angle - option['angle']
    return [rotate(origin, point, angle) for point in mline_box]


def make_mline_boxes_options(mline_boxes: List) -> Tuple[int, int, List[Dict]]:
    options = []
    w_max = 0
    w_max_idx = -1
    for mline_idx, mline_box in enumerate(mline_boxes):
        w = distance(mline_box[0], mline_box[1])
        if w_max < w:
            w_max = w
            w_max_idx = mline_idx
        angle = (fline(mline_box[0], mline_box[1]))[2]
        options.append({
            'w': w,
            'angle': angle
        })
    return w_max, w_max_idx, options


def fix_mline_boxes_angle(mline_boxes: List) -> Tuple[List, float]:
    max_delta_angle = 7
    w_max, w_max_idx, options = make_mline_boxes_options(mline_boxes)
    target_angle = options[w_max_idx]['angle']
    for mline_idx, mline_box in enumerate(mline_boxes):
        if abs(target_angle - options[mline_idx]['angle']) > max_delta_angle:
            mline_boxes[mline_idx] = fix_box_angle(target_angle, mline_box, options[mline_idx])
    return mline_boxes, target_angle


def check_line_side_faces(target_points: np.ndarray, shape: Tuple) -> Tuple[List, Dict]:
    """
    Неработающая заглушка
    которая должна фиксить угол наклона боковых граней.
    """
    w = shape[1]
    out_of_bounds_points = []
    out_of_bounds_points_idx = {}
    for idx, point in enumerate(target_points):
        if point[0] < 0 or point[0] > w:
            out_of_bounds_points.append(idx)
            out_of_bounds_points_idx[idx] = True
        else:
            out_of_bounds_points_idx[idx] = False
    return out_of_bounds_points, out_of_bounds_points_idx


def get_center_point(p0: List, p1: List) -> List[float]:
    """
    Ищем середину отрезка, заданного 2 точками
    :param p0:
    :param p1:
    :return:
    """
    return [(p0[0]+p1[0])/2, (p0[1]+p1[1])/2]


def calc_diff(p1: List, p2: np.ndarray) -> Tuple[float, float]:
    return p1[0]-p2[0], p1[1]-p2[1]


def apply_new_point(point: List, dx: float, dy: float) -> List[float]:
    return [point[0]+dx, point[1]+dy]


def apply_new_box_angle(box: List, dx: float, dy: float) -> List[np.ndarray]:
    left_reference_point = get_center_point(box[3], box[0])
    right_reference_point = get_center_point(box[1], box[2])
    top_matrix = linear_line_matrix(box[0], box[1])
    bottom_matrix = linear_line_matrix(box[3], box[2])

    left_matrix = linear_line_matrix(left_reference_point, apply_new_point(left_reference_point, dx, dy))
    right_matrix = linear_line_matrix(right_reference_point, apply_new_point(right_reference_point, dx, dy))

    return [
        detect_intersection(left_matrix, top_matrix),
        detect_intersection(top_matrix, right_matrix),
        detect_intersection(right_matrix, bottom_matrix),
        detect_intersection(bottom_matrix, left_matrix)
    ]


def build_new_points(left_reference_point: List, right_reference_point: List, dx: float, dy: float) -> List[List]:
    return [
        apply_new_point(left_reference_point, dx, dy),
        apply_new_point(left_reference_point, -dx, -dy),
        apply_new_point(right_reference_point, -dx, -dy),
        apply_new_point(right_reference_point, dx, dy)
    ]


def fit_to_frame(target_points: np.ndarray or List, mline_boxes: List,  shape: Tuple) -> Tuple[List, List]:
    """
    Неработающая заглушка
    которая должна вписывать область с текстом в заданную рамку
    """
    h = shape[0]
    w = shape[1]
    out_of_bounds_points, out_of_bounds_points_idx = check_line_side_faces(target_points, shape)
    if len(out_of_bounds_points):
        left_reference_point = get_center_point(target_points[0], target_points[1])
        right_reference_point = get_center_point(target_points[2], target_points[3])
        reference_point_angle = (fline(left_reference_point, right_reference_point))[2]
        center_matrix = linear_line_matrix(left_reference_point, right_reference_point)
        top_matrix = linear_line_matrix(target_points[1], target_points[2])
        bottom_matrix = linear_line_matrix(target_points[0], target_points[3])
        if left_reference_point[0] < 0:
            left_reference_point = [0, get_y_by_matrix(center_matrix, 0)]
        if right_reference_point[0] > w:
            right_reference_point = [w, get_y_by_matrix(center_matrix, w)]
        if reference_point_angle > 0:
            p2_matrix = top_matrix
            p0_matrix = bottom_matrix
        else:
            p2_matrix = bottom_matrix
            p0_matrix = top_matrix
        p2_new = detect_intersection(p2_matrix, linear_line_matrix([w, 0], [w, h]))
        p0_new = detect_intersection(p0_matrix, linear_line_matrix([0, 0], [0, h]))
        p2_dx = w - right_reference_point[0]
        p0_dx = left_reference_point[0]
        if p2_dx > p0_dx:
            dx, dy = calc_diff(left_reference_point, p0_new)
        else:
            dx, dy = calc_diff(right_reference_point, p2_new)
            dx = -dx
            dy = -dy
        target_points = build_new_points(left_reference_point, right_reference_point, dx, dy)
        mline_boxes = [apply_new_box_angle(mline_box, dx, dy) for mline_box in mline_boxes]
    return target_points, mline_boxes


def make_boxes(img: np.ndarray,
               boxes: List,
               color: Tuple[int, int, int] = (0, 0, 255),
               thickness: int = 2) -> np.ndarray:
    for box in boxes:
        polybox = np.array(box).astype(np.int32).reshape((-1))
        polybox = polybox.reshape(-1, 2)
        cv2.polylines(img, [polybox.reshape((-1, 1, 2))], True, color, thickness)
    return img


def resize(img: np.ndarray, scale_coef: float) -> np.ndarray:
    width = int(img.shape[1] * scale_coef)
    height = int(img.shape[0] * scale_coef)
    dim = (width, height)
    return cv2.resize(img, dim, interpolation=cv2.INTER_AREA)


def resize_coordinates(points_arr: List, scale_coef: float) -> List:
    return [np.round(np.array(points)*scale_coef).tolist() for points in points_arr]


def add_coordinates_offset(points: List or np.ndarray, x: float, y: float) -> List:
    """
    TODO: describe function
    """
    return [[point[0] + x, point[1] + y] for point in points]


def apply_coefficient(points: List or np.ndarray, coef_w: float, coef_h: float) -> List:
    """
    TODO: resize points coordinates
    """
    return [[point[0] * coef_w, point[1] * coef_h] for point in points]


