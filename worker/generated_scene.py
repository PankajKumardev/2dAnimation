from manim import *

class RedisQueueScene(Scene):
    def construct(self):
        queue_box = Rectangle(width=4, height=2, color=BLUE)
        queue_label = Text("Redis Queue", color=WHITE).scale(0.7).move_to(queue_box.get_center())
        self.play(Create(queue_box), Write(queue_label))

        enqueue_arrow = Arrow(start=LEFT * 2, end=queue_box.get_left() + LEFT * 0.3, buff=0.2)
        enqueue_label = Text("Enqueue", color=YELLOW).scale(0.5).next_to(enqueue_arrow, UP)
        self.play(Create(enqueue_arrow), Write(enqueue_label))

        dequeue_arrow = Arrow(start=queue_box.get_right() + RIGHT * 0.3, end=RIGHT * 2, buff=0.2)
        dequeue_label = Text("Dequeue", color=GREEN).scale(0.5).next_to(dequeue_arrow, UP)
        self.play(Create(dequeue_arrow), Write(dequeue_label))
        
        self.wait(2)