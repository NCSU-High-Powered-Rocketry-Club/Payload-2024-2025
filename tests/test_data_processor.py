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
        (
            "data_packet",
        ),
        [
            (
                make_data_packet(
                    timestamp=0*1e3,
                    estCompensatedAccelX=0,
                    estCompensatedAccelY=0,
                    estCompensatedAccelZ=-9.8,
                    magneticFieldX=2.18750000,
                    magneticFieldY=34.43750000,
                    magneticFieldZ=-43.06250000,
                ),
            ),
            (
                make_data_packet(
                    timestamp=0*1e3,
                    estCompensatedAccelX=0,
                    estCompensatedAccelY=0,
                    estCompensatedAccelZ=-9.8,
                    magneticFieldX=-44.5,
                    magneticFieldY=1.3125,
                    magneticFieldZ=-43.375,
                ),
            ),
            (
                make_data_packet(
                    timestamp=0*1e3,
                    estCompensatedAccelX=0,
                    estCompensatedAccelY=0,
                    estCompensatedAccelZ=-9.8,
                    magneticFieldX=-9.43750000,
                    magneticFieldY=-42.25000000,
                    magneticFieldZ=-40.50000000,
                ),
            ),
            (
                make_data_packet(
                    timestamp=0*1e3,
                    estCompensatedAccelX=0,
                    estCompensatedAccelY=0,
                    estCompensatedAccelZ=-9.8,
                    magneticFieldX=30.6875,
                    magneticFieldY=-2.4375,
                    magneticFieldZ=-41.6875,
                ),
            ),
            (
                make_data_packet(
                    timestamp=0*1e3,
                    estCompensatedAccelX=0,
                    estCompensatedAccelY=0,
                    estCompensatedAccelZ=9.8,
                    magneticFieldX=42.18750000,
                    magneticFieldY=5.93750000,
                    magneticFieldZ=46.00000000,
                ),
            ),
            (
                make_data_packet(
                    timestamp=0*1e3,
                    estCompensatedAccelX=0,
                    estCompensatedAccelY=0,
                    estCompensatedAccelZ=9.8,
                    magneticFieldX=5.56250000,
                    magneticFieldY=-45.18750000,
                    magneticFieldZ=46.93750000,
                ),
            ),
            (
                make_data_packet(
                    timestamp=0*1e3,
                    estCompensatedAccelX=0,
                    estCompensatedAccelY=0,
                    estCompensatedAccelZ=9.8,
                    magneticFieldX=-37.31250000,
                    magneticFieldY=-18.37500000,
                    magneticFieldZ=40.81250000,
                ),
            ),
            (
                make_data_packet(
                    timestamp=0*1e3,
                    estCompensatedAccelX=0,
                    estCompensatedAccelY=0,
                    estCompensatedAccelZ=9.8,
                    magneticFieldX=-41.25000000,
                    magneticFieldY=-14.81250000,
                    magneticFieldZ=41.62500000,
                ),
            ),
            (
                make_data_packet(
                    timestamp=0*1e3,
                    estCompensatedAccelX=0,
                    estCompensatedAccelY=-9.8,
                    estCompensatedAccelZ=0,
                    magneticFieldX=1.50000000,
                    magneticFieldY=-41.43750000,
                    magneticFieldZ=-40.31250000,
                ),
            ),
            (
                make_data_packet(
                    timestamp=0*1e3,
                    estCompensatedAccelX=0,
                    estCompensatedAccelY=-9.8,
                    estCompensatedAccelZ=0,
                    magneticFieldX=-38.93750000,
                    magneticFieldY=-38.12500000,
                    magneticFieldZ=0.81250000,
                ),
            ),
            (
                make_data_packet(
                    timestamp=0*1e3,
                    estCompensatedAccelX=0,
                    estCompensatedAccelY=-9.8,
                    estCompensatedAccelZ=0,
                    magneticFieldX=19.81250000,
                    magneticFieldY=-34.50000000,
                    magneticFieldZ=44.62500000,
                ),
            ),
            (
                make_data_packet(
                    timestamp=0*1e3,
                    estCompensatedAccelX=0,
                    estCompensatedAccelY=-9.8,
                    estCompensatedAccelZ=0,
                    magneticFieldX=42.18750000,
                    magneticFieldY=-37.75000000,
                    magneticFieldZ=0.93750000,
                ),
            ),

        ],
        ids=["neg_z_mag_N","neg_z_mag_E","neg_z_mag_S","neg_z_mag_W",
             "pos_z_mag_N","pos_z_mag_E","pos_z_mag_S","pos_z_mag_W",
             "neg_y_mag_N","neg_y_mag_E","neg_y_mag_S","neg_y_mag_W",],
    )
    def test_first_update_orientation(self, data_processor, data_packet):
        """
        Tests whether the update() method works correctly, for the first update() call,
        along with get_processor_data_packets()
        """
        d = data_processor
        d._data_packet = data_packet
        d._first_update()
        rot_acc = d._current_orientation_quaternions.apply([
            data_packet.estCompensatedAccelX,
            data_packet.estCompensatedAccelY,
            data_packet.estCompensatedAccelZ,
        ])
        np.testing.assert_allclose(rot_acc, np.array([0,0,9.8]), rtol=0.1)


