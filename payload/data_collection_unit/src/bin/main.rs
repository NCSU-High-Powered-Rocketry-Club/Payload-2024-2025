#![no_std]
#![no_main]

use defmt::{debug, info};
use embassy_executor::{task, Spawner};
use embassy_sync::blocking_mutex::raw::NoopRawMutex;
use embassy_sync::channel::Channel;
use embassy_time::{Duration, Timer};
use esp_hal::clock::CpuClock;
use esp_hal::timer::timg::TimerGroup;
use esp_hal::uart::Uart;
use esp_hal::Async;
use esp_println as _;

#[panic_handler]
fn panic(_: &core::panic::PanicInfo) -> ! {
    loop {}
}

#[derive(Debug)]
struct GpsPosition {
    lat: f64,
    long: f64,
    alt: f64,
}

const GPS_CHANNEL: Channel<embassy_sync::blocking_mutex::raw::NoopRawMutex, GpsPosition, 64> =
    Channel::new();

#[task]
async fn gps_fetch(uart: Uart<'static, Async>) {
    let mut parser_buf = [0; 256];
    let parser_buf = ublox::FixedLinearBuffer::new(&mut parser_buf[..]);
    let mut parser = ublox::Parser::new(parser_buf);

    loop {
        let mut buf = [0; 32];
        match uart.read_exact_async(buf).await {
            Ok(_) => {
                let mut it = parser.consume(&buf);

                loop {
                    let packet = match it.next() {
                        Some(Ok(packet)) => packet,
                        Some(Err(_)) => {
                            continue;
                        }
                        None => break,
                    };

                    let pos = match packet {
                        ublox::PacketRef::NavPosLlh(nav_pos_llh_ref) => GpsPosition {
                            lat: nav_pos_llh_ref.lat_degrees(),
                            long: nav_pos_llh_ref.lon_degrees(),
                            alt: nav_pos_llh_ref.height_meters(),
                        },
                        _ => {
                            continue;
                        }
                    };

                    GPS_CHANNEL.send(pos).await;
                }
            }
            Err(_) => {}
        }
    }
}

#[esp_hal_embassy::main]
async fn main(spawner: Spawner) {
    let config = esp_hal::Config::default().with_cpu_clock(CpuClock::max());
    let peripherals = esp_hal::init(config);

    let timer0 = TimerGroup::new(peripherals.TIMG1);
    esp_hal_embassy::init(timer0.timer0);

    info!("Embassy initialized!");

    {
        // TODO: Check these
        let baud = 10;
        let uart_tx = peripherals.GPIO10;
        let uart_rx = peripherals.GPIO9;

        let uart = esp_hal::uart::Uart::new(
            peripherals.UART1,
            esp_hal::uart::Config::default().with_baudrate(baud),
        )
        .unwrap()
        .with_rx(uart_rx)
        .with_tx(uart_tx)
        .into_async();

        spawner.spawn(gps_fetch(uart)).unwrap();
    }

    loop {
        info!("Hello world!");
        loop {
            match GPS_CHANNEL.try_receive() {
                Ok(pos) => {
                    debug!("{:?}", pos);
                }
                Err(_) => break,
            }
        }
        Timer::after(Duration::from_secs(1)).await;
    }
}
