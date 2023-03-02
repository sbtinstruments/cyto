from ._outline import OutlineReceiveStream


async def outline_to_stdout(receive_stream: OutlineReceiveStream) -> None:
    async with receive_stream:
        async for outline in receive_stream:
            outline.pretty_print()
