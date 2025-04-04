"""Tests DataProcessor class."""

import numpy as np
import pytest
from scipy.spatial.transform import Rotation as R

from payload.data_handling.data_processor import DataProcessor
from payload.data_handling.packets.imu_data_packet import IMUDataPacket


@pytest.fixture
def data_processor():
    return DataProcessor()


def make_data_packet(**kwargs) -> IMUDataPacket:
    """Creates an EstimatedDataPacket with the specified keyword arguments. Provides dummy values
    for arguments not specified."""

    dummy_values = {k: 1.123456789 for k in IMUDataPacket.__struct_fields__}
    return IMUDataPacket(**{**dummy_values, **kwargs})


class TestDataProcessor:
    """Tests the DataProcessor class"""

    @pytest.mark.parametrize(
        "data_packet",
        [
            make_data_packet(
                estCompensatedAccelX=0,
                estCompensatedAccelY=0,
                estCompensatedAccelZ=-9.8,
                magneticFieldX=2.1875,
                magneticFieldY=34.4375,
                magneticFieldZ=-43.0625,
            ),
            make_data_packet(
                estCompensatedAccelX=0,
                estCompensatedAccelY=0,
                estCompensatedAccelZ=-9.8,
                magneticFieldX=-44.5,
                magneticFieldY=1.3125,
                magneticFieldZ=-43.375,
            ),
            make_data_packet(
                estCompensatedAccelX=0,
                estCompensatedAccelY=0,
                estCompensatedAccelZ=-9.8,
                magneticFieldX=-9.4375,
                magneticFieldY=-42.25,
                magneticFieldZ=-40.5,
            ),
            make_data_packet(
                estCompensatedAccelX=0,
                estCompensatedAccelY=0,
                estCompensatedAccelZ=-9.8,
                magneticFieldX=30.6875,
                magneticFieldY=-2.4375,
                magneticFieldZ=-41.6875,
            ),
            make_data_packet(
                estCompensatedAccelX=0,
                estCompensatedAccelY=0,
                estCompensatedAccelZ=9.8,
                magneticFieldX=42.1875,
                magneticFieldY=5.9375,
                magneticFieldZ=46.0,
            ),
            make_data_packet(
                estCompensatedAccelX=0,
                estCompensatedAccelY=0,
                estCompensatedAccelZ=9.8,
                magneticFieldX=5.5625,
                magneticFieldY=-45.1875,
                magneticFieldZ=46.9375,
            ),
            make_data_packet(
                estCompensatedAccelX=0,
                estCompensatedAccelY=0,
                estCompensatedAccelZ=9.8,
                magneticFieldX=-37.3125,
                magneticFieldY=-18.375,
                magneticFieldZ=40.8125,
            ),
            make_data_packet(
                estCompensatedAccelX=0,
                estCompensatedAccelY=0,
                estCompensatedAccelZ=9.8,
                magneticFieldX=-41.25,
                magneticFieldY=-14.8125,
                magneticFieldZ=41.625,
            ),
            make_data_packet(
                estCompensatedAccelX=0,
                estCompensatedAccelY=-9.8,
                estCompensatedAccelZ=0,
                magneticFieldX=1.5,
                magneticFieldY=-41.4375,
                magneticFieldZ=-40.3125,
            ),
            make_data_packet(
                estCompensatedAccelX=0,
                estCompensatedAccelY=-9.8,
                estCompensatedAccelZ=0,
                magneticFieldX=-38.9375,
                magneticFieldY=-38.125,
                magneticFieldZ=0.8125,
            ),
            make_data_packet(
                estCompensatedAccelX=0,
                estCompensatedAccelY=-9.8,
                estCompensatedAccelZ=0,
                magneticFieldX=19.8125,
                magneticFieldY=-34.5,
                magneticFieldZ=44.625,
            ),
            make_data_packet(
                estCompensatedAccelX=0,
                estCompensatedAccelY=-9.8,
                estCompensatedAccelZ=0,
                magneticFieldX=42.1875,
                magneticFieldY=-37.75,
                magneticFieldZ=0.9375,
            ),
            make_data_packet(
                estCompensatedAccelX=0,
                estCompensatedAccelY=9.8,
                estCompensatedAccelZ=0,
                magneticFieldX=-3.8125,
                magneticFieldY=37.3125,
                magneticFieldZ=-41.0625,
            ),
            make_data_packet(
                estCompensatedAccelX=0,
                estCompensatedAccelY=9.8,
                estCompensatedAccelZ=0,
                magneticFieldX=44.375,
                magneticFieldY=37.3125,
                magneticFieldZ=-4.4375,
            ),
            make_data_packet(
                estCompensatedAccelX=0,
                estCompensatedAccelY=9.8,
                estCompensatedAccelZ=0,
                magneticFieldX=4.875,
                magneticFieldY=33.875,
                magneticFieldZ=42.5,
            ),
            make_data_packet(
                estCompensatedAccelX=0,
                estCompensatedAccelY=9.8,
                estCompensatedAccelZ=0,
                magneticFieldX=-45.375,
                magneticFieldY=33.6875,
                magneticFieldZ=-4.5625,
            ),
            make_data_packet(
                estCompensatedAccelX=-9.8,
                estCompensatedAccelY=0,
                estCompensatedAccelZ=0,
                magneticFieldX=-42.5,
                magneticFieldY=-2.3125,
                magneticFieldZ=-38.6875,
            ),
            make_data_packet(
                estCompensatedAccelX=-9.8,
                estCompensatedAccelY=0,
                estCompensatedAccelZ=0,
                magneticFieldX=-41.375,
                magneticFieldY=40.5625,
                magneticFieldZ=-3.0,
            ),
            make_data_packet(
                estCompensatedAccelX=-9.8,
                estCompensatedAccelY=0,
                estCompensatedAccelZ=0,
                magneticFieldX=-36.0625,
                magneticFieldY=-1.875,
                magneticFieldZ=43.00,
            ),
            make_data_packet(
                estCompensatedAccelX=-9.8,
                estCompensatedAccelY=0,
                estCompensatedAccelZ=0,
                magneticFieldX=-40.9375,
                magneticFieldY=-41.9375,
                magneticFieldZ=-0.25,
            ),
            make_data_packet(
                estCompensatedAccelX=9.4,
                estCompensatedAccelY=0.2,
                estCompensatedAccelZ=-0.5,
                magneticFieldX=46.875,
                magneticFieldY=-8.9375,
                magneticFieldZ=-30.9375,
            ),
            make_data_packet(
                estCompensatedAccelX=9.8,
                estCompensatedAccelY=0,
                estCompensatedAccelZ=0,
                magneticFieldX=47.625,
                magneticFieldY=-32.125,
                magneticFieldZ=11.875,
            ),
            make_data_packet(
                estCompensatedAccelX=9.8,
                estCompensatedAccelY=0,
                estCompensatedAccelZ=0,
                magneticFieldX=45.5,
                magneticFieldY=-0.3125,
                magneticFieldZ=36.9375,
            ),
            make_data_packet(
                estCompensatedAccelX=9.8,
                estCompensatedAccelY=0,
                estCompensatedAccelZ=0,
                magneticFieldX=47,
                magneticFieldY=29.1875,
                magneticFieldZ=-6.75,
            ),
        ],
        ids=[
            "neg_z_mag_N",
            "neg_z_mag_E",
            "neg_z_mag_S",
            "neg_z_mag_W",
            "pos_z_mag_N",
            "pos_z_mag_E",
            "pos_z_mag_S",
            "pos_z_mag_W",
            "neg_y_mag_N",
            "neg_y_mag_E",
            "neg_y_mag_S",
            "neg_y_mag_W",
            "pos_y_mag_N",
            "pos_y_mag_E",
            "pos_y_mag_S",
            "pos_y_mag_W",
            "neg_x_mag_N",
            "neg_x_mag_E",
            "neg_x_mag_S",
            "neg_x_mag_W",
            "pos_x_mag_N",
            "pos_x_mag_E",
            "pos_x_mag_S",
            "pos_x_mag_W",
        ],
    )
    def test_first_update_orientation(self, data_processor, data_packet):
        """
        Tests whether the update() method works correctly, for the first update() call,
        along with get_processor_data_packets()
        """
        d = data_processor
        d._data_packet = data_packet
        d._first_update()
        print(d._current_orientation_quaternions)
        rot_acc = R.from_quat(d._current_orientation_quaternions, scalar_first=True).apply(
            [
                data_packet.estCompensatedAccelX,
                data_packet.estCompensatedAccelY,
                data_packet.estCompensatedAccelZ,
            ]
        )
        np.testing.assert_allclose(rot_acc, np.array([0, 0, 9.8]), atol=0.5)
