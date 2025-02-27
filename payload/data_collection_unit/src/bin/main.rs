#![no_std]
#![no_main]
#![allow(unused)]

use core::cell::RefCell;
use core::default;

use embedded_hal_bus::i2c::RefCellDevice;
use esp_hal::delay::Delay;
use micromath::F32Ext;

use defmt::{debug, info};
use embassy_executor::{task, Spawner};
use embassy_sync::blocking_mutex::raw::{CriticalSectionRawMutex, NoopRawMutex};
use embassy_sync::channel::Channel;
use embassy_time::{Duration, Timer};
use esp_backtrace as _;
use esp_hal::clock::CpuClock;
use esp_hal::gpio::OutputPin;
use esp_hal::i2c::master::I2c;
use esp_hal::timer::timg::TimerGroup;
use esp_hal::uart::Uart;
use esp_hal::{time, Async};
use esp_println as _;
use ublox::{CfgMsgAllPortsBuilder, CfgPrtUartBuilder, NavPosLlh, NavPvt};

struct DataPacket {
    timestamp: f32,
    voltage: f32,
    temperature: f32,
    pressure: f32,
    altitude: f32,
    comp_accel_x: f32,
    comp_accel_y: f32,
    comp_accel_z: f32,
    gyro_x: f32,
    gyro_y: f32,
    gyro_z: f32,
    magnetic_x: f32,
    magnetic_y: f32,
    magnetic_z: f32,
    quat_w: f32,
    quat_x: f32,
    quat_y: f32,
    quat_z: f32,
    gps_lat: f32,
    gps_long: f32,
    gps_alt: f32,
}

impl DataPacket {
    fn send(&self) {}

    fn pretty_print(&self) {
        info!("=== DataPacket ===");
        info!("Timestamp: ");
        info!("{}", self.timestamp);
        info!("Voltage: ");
        info!("{}", self.voltage);
        info!("Temperature: ");
        info!("{}", self.temperature);
        info!("Pressure: ");
        info!("{}", self.pressure);
        info!("Comp Accel X: ");
        info!("{}", self.comp_accel_x);
        info!("Comp Accel Y: ");
        info!("{}", self.comp_accel_y);
        info!("Comp Accel Z: ");
        info!("{}", self.comp_accel_z);
        info!("Gyro X: ");
        info!("{}", self.gyro_x);
        info!("Gyro Y: ");
        info!("{}", self.gyro_y);
        info!("Gyro Z: ");
        info!("{}", self.gyro_z);
        info!("Magnetic X: ");
        info!("{}", self.magnetic_x);
        info!("Magnetic Y: ");
        info!("{}", self.magnetic_y);
        info!("Magnetic Z: ");
        info!("{}", self.magnetic_z);
        info!("Quat W: ");
        info!("{}", self.quat_w);
        info!("Quat X: ");
        info!("{}", self.quat_x);
        info!("Quat Y: ");
        info!("{}", self.quat_y);
        info!("Quat Z: ");
        info!("{}", self.quat_z);
        info!("GPS Lat: ");
        info!("{}", self.gps_lat);
        info!("GPS Long: ");
        info!("{}", self.gps_long);
        info!("GPS Alt: ");
        info!("{}", self.gps_alt);
        info!("==================");
    }
}

#[derive(Debug, Default)]
struct GpsPosition {
    lat: f64,
    long: f64,
    alt: f64,
}

const GPS_CHANNEL: Channel<CriticalSectionRawMutex, GpsPosition, 64> = Channel::new();

#[task]
async fn gps_fetch(mut uart: Uart<'static, Async>) {
    let mut parser_buf = [0; 256];
    let parser_buf = ublox::FixedLinearBuffer::new(&mut parser_buf[..]);
    let mut parser = ublox::Parser::new(parser_buf);

    loop {
        // info!("Start of loop");
        let mut buf = [0; 32];
        match uart.read_exact_async(&mut buf).await {
            Ok(_) => {
                // info!("got read");
                // info!("{:?}", buf);
                let mut it = parser.consume(&buf);

                loop {
                    let packet = match it.next() {
                        Some(Ok(packet)) => packet,
                        Some(Err(_)) => {
                            info!("!!!!!!!!!!!!Corrupted packet");
                            continue;
                        }
                        None => {
                            // info!("no packets");
                            break;
                        }
                    };
                    // info!("Got here");

                    let pos = match packet {
                        // ublox::PacketRef::NavPosLlh(nav_pos_llh_ref) => GpsPosition {
                        //     lat: nav_pos_llh_ref.lat_degrees(),
                        //     long: nav_pos_llh_ref.lon_degrees(),
                        //     alt: nav_pos_llh_ref.height_meters(),
                        // },
                        ublox::PacketRef::NavPvt(nav) => {
                            match nav.fix_type() {
                                ublox::GpsFix::NoFix => info!("No fix"),
                                ublox::GpsFix::DeadReckoningOnly => info!("DeadReckoningOnly "),
                                ublox::GpsFix::Fix2D => info!("Fix2D "),
                                ublox::GpsFix::Fix3D => info!("Fix3D"),
                                ublox::GpsFix::GPSPlusDeadReckoning => {
                                    info!("GPSPlusDeadReckoning")
                                }
                                ublox::GpsFix::TimeOnlyFix => info!("TimeOnlyFix"),
                                _ => {}
                            }
                            GpsPosition {
                                lat: nav.lat_degrees(),
                                long: nav.lon_degrees(),
                                alt: nav.height_meters(),
                            }
                        }
                        _ => {
                            info!("other type of packet");
                            continue;
                        }
                    };

                    info!("!!!!!!!!!!!!!got position! {:?}", pos.lat);
                    info!("!!!!!!!!!!!!!got position! {:?}", pos.long);
                    info!("!!!!!!!!!!!!!got position! {:?}", pos.alt);
                    debug!("got position! {:?}", pos.alt);

                    GPS_CHANNEL.try_send(pos).unwrap();
                    info!("{}", GPS_CHANNEL.len());
                }
            }
            Err(_) => {
                // info!("did not got read");
            }
        }
        Timer::after(Duration::from_millis(10)).await;
    }
}

fn pressure_to_altitude(pressure: f32) -> f32 {
    //   altitude = 44330 * (1.0 - pow((_pressure / 100) / seaLevelhPa, 0.1903));
    let sea_levelh_pa = 1013.25;
    44330.0 * (1.0 - ((pressure / 100.0) / sea_levelh_pa).powf(0.1903))
}

#[esp_hal_embassy::main]
async fn main(spawner: Spawner) {
    let config = esp_hal::Config::default().with_cpu_clock(CpuClock::max());
    let peripherals = esp_hal::init(config);

    let timer0 = TimerGroup::new(peripherals.TIMG1);
    esp_hal_embassy::init(timer0.timer0);

    info!("Embassy initialized!");
    let start_time = time::Instant::now();

    // {
    //     let baud = 9600;
    //     let uart_tx = peripherals.GPIO22;
    //     let uart_rx = peripherals.GPIO21;

    //     let mut uart = esp_hal::uart::Uart::new(
    //         peripherals.UART1,
    //         esp_hal::uart::Config::default().with_baudrate(baud),
    //     )
    //     .unwrap()
    //     .with_rx(uart_rx)
    //     .with_tx(uart_tx)
    //     .into_async();

    //     uart.write_async(
    //         &CfgMsgAllPortsBuilder::set_rate_for::<NavPvt>([0, 1, 1, 1, 0, 0]).into_packet_bytes(),
    //         // &CfgMsgAllPortsBuilder::set_rate_for::<NavPosLlh>([0, 1, 1, 1, 0, 0]).into_packet_bytes(),
    //     )
    //     .await
    //     .unwrap();

    //     spawner.spawn(gps_fetch(uart)).unwrap();
    // }

    let scl = peripherals.GPIO22;
    let sda = peripherals.GPIO21;
    let i2c =
        esp_hal::i2c::master::I2c::new(peripherals.I2C1, esp_hal::i2c::master::Config::default())
            .unwrap()
            .with_scl(scl)
            .with_sda(sda)
            .into_async();

    let i2c = RefCell::new(i2c);

    let mut delay_source = Delay::new();
    let mut imu = {
        let bno_interface = bno080::interface::I2cInterface::new(RefCellDevice::new(&i2c), 0x4A); // might be 0x4B
        let mut imu = bno080::wrapper::BNO080::new_with_interface(bno_interface);
        imu.init(&mut delay_source);
        let millis_between_reports = 40;
        imu.enable_gyro(millis_between_reports).unwrap();
        // TODO: this should be non linear accel
        imu.enable_linear_accel(millis_between_reports).unwrap();
        imu.enable_rotation_vector(millis_between_reports).unwrap();
        imu
    };

    let mut pressure_sensor = {
        let mut pressure_sensor: dps310::DPS310<_> =
            match dps310::DPS310::new(RefCellDevice::new(&i2c), 0x77, &dps310::Config::new()) {
                Ok(p) => p,
                Err(e) => match e {
                    dps310::Error::I2CError(e) => match e {
                        esp_hal::i2c::master::Error::FifoExceeded => todo!(),
                        esp_hal::i2c::master::Error::AcknowledgeCheckFailed(
                            acknowledge_check_failed_reason,
                        ) => todo!(),
                        esp_hal::i2c::master::Error::Timeout => todo!(),
                        esp_hal::i2c::master::Error::ArbitrationLost => todo!(),
                        esp_hal::i2c::master::Error::ExecutionIncomplete => todo!(),
                        esp_hal::i2c::master::Error::CommandNumberExceeded => todo!(),
                        esp_hal::i2c::master::Error::ZeroLengthInvalid => todo!(),
                        _ => todo!(),
                    },
                    dps310::Error::InvalidMeasurementMode => todo!(),
                },
            };

        pressure_sensor.read_calibration_coefficients().unwrap();
        pressure_sensor
            .trigger_measurement(true, true, true)
            .unwrap();

        pressure_sensor
    };

    loop {
        let imu_count = imu.handle_all_messages(&mut delay_source, 100);
        if imu_count == 0 {
            // TODO: IMU Error (probably)
        }

        let accel = imu.linear_accel().unwrap();
        let [comp_accel_x, comp_accel_y, comp_accel_z] = accel;
        let rot = imu.rotation_quaternion().unwrap();
        let [quat_x, quat_y, quat_z, quat_w] = rot;
        let gyro = imu.gyro().unwrap();
        let [gyro_x, gyro_y, gyro_z] = gyro;

        // TODO
        let [magnetic_x, magnetic_y, magnetic_z] = [0.0, 0.0, 0.0];

        let mut pos: GpsPosition = GpsPosition::default();
        loop {
            match GPS_CHANNEL.try_receive() {
                Ok(new_pos) => pos = new_pos,
                Err(_) => break,
            }
        }
        let gps_lat = pos.lat as f32;
        let gps_long = pos.long as f32;
        let gps_alt = pos.alt as f32;

        // if pressure_sensor
        let pressure = pressure_sensor.read_pressure_calibrated().unwrap();
        let temperature = pressure_sensor.read_temp_calibrated().unwrap();
        let altitude = pressure_to_altitude(pressure);

        let timestamp = start_time.elapsed().as_millis() as f32;
        let voltage = 0.0; // TODO
        let data_packet = DataPacket {
            timestamp,
            voltage,
            temperature,
            pressure,
            altitude,
            comp_accel_x,
            comp_accel_y,
            comp_accel_z,
            gyro_x,
            gyro_y,
            gyro_z,
            magnetic_x,
            magnetic_y,
            magnetic_z,
            quat_w,
            quat_x,
            quat_y,
            quat_z,
            gps_lat,
            gps_long,
            gps_alt,
        };

        data_packet.pretty_print();

        Timer::after(Duration::from_secs(1)).await;
    }
}
