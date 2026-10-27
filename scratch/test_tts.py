import asyncio
import edge_tts

async def main():
    try:
        c = edge_tts.Communicate("Hola Sebastian, la voz está lista.", "es-MX-JorgeNeural")
        await c.save("data/test_voice.mp3")
        print("Guardado con exito!")
    except Exception as e:
        print("Error:", e)

if __name__ == "__main__":
    asyncio.run(main())
